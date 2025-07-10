# processor_client.py
from concurrent.futures import ThreadPoolExecutor, as_completed
import docker
import threading
import queue
import time
import os
import logging
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ContainerPool')

@dataclass
class ContainerConfig:
    """容器配置类"""
    input_mount: str = "/app/input"
    output_mount: str = "/app/output"
    image: str = "json-processor:latest"
    max_containers: int = 5
    idle_timeout: int = 300  # 空闲容器超时时间（秒）
    max_retries: int = 3     # 容器启动失败重试次数

class ContainerPool:
    """企业级容器池管理器（优化关闭版本）"""
    
    def __init__(self, config: ContainerConfig, input_dir: str, output_dir: str):
        self.client = docker.from_env()
        self.config = config
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        
        # 确保目录存在
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 容器池数据结构
        self.available_containers = queue.Queue(maxsize=config.max_containers)
        self.active_containers = {}
        self.lock = threading.Lock()
        self.container_timestamps = {}  # 存储容器的最后使用时间
        
        # 监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_pool, daemon=True)
        self.running = True
        self.monitor_thread.start()
        
        logger.info(f"Container pool initialized with max {config.max_containers} containers")
    
    def _create_container(self, retry_count=0):
        """创建并启动一个新容器"""
        try:
            container = self.client.containers.run(
                image=self.config.image,
                volumes={
                    self.input_dir: {'bind': self.config.input_mount, 'mode': 'ro'},
                    self.output_dir: {'bind': self.config.output_mount, 'mode': 'rw'}
                },
                detach=True
            )
            
            # 等待容器启动完成
            time.sleep(0.5)
            
            # 检查容器状态
            container.reload()
            if container.status != 'running':
                raise RuntimeError(f"Container {container.id[:12]} failed to start: status {container.status}")
            
            # 记录创建时间
            self.container_timestamps[container.id] = time.time()
            
            logger.info(f"Container created: {container.id[:12]}")
            return container
        
        except Exception as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Container creation failed (attempt {retry_count+1}/{self.config.max_retries}): {str(e)}")
                time.sleep(1)
                return self._create_container(retry_count + 1)
            else:
                logger.error(f"Failed to create container after {self.config.max_retries} attempts: {str(e)}")
                raise
    
    def _monitor_pool(self):
        """监控容器池状态，维护容器数量"""
        while self.running:
            try:
                # 检查当前池大小
                with self.lock:
                    current_count = self.available_containers.qsize() + len(self.active_containers)
                    
                    # 添加容器直到达到最大数量
                    while current_count < self.config.max_containers:
                        try:
                            container = self._create_container()
                            self.available_containers.put(container)
                            current_count += 1
                        except Exception as e:
                            logger.error(f"Failed to add container to pool: {str(e)}")
                            break
                
                # 清理空闲超时的容器
                self._cleanup_idle_containers()
                
                # 定期检查
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in pool monitor: {str(e)}")
                time.sleep(5)
    
    def _cleanup_idle_containers(self):
        """清理空闲超时的容器"""
        with self.lock:
            # 创建临时队列以检查空闲时间
            temp_queue = queue.Queue()
            removed_count = 0
            
            # 处理可用容器
            while not self.available_containers.empty():
                container = self.available_containers.get()
                
                # 检查是否空闲超时
                if time.time() - self.container_timestamps.get(container.id, 0) > self.config.idle_timeout:
                    try:
                        # 使用带超时的停止方法
                        if self._stop_container(container):
                            removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove idle container {container.id[:12]}: {str(e)}")
                        # 放回队列
                        temp_queue.put(container)
                else:
                    temp_queue.put(container)
            
            # 将未超时的容器放回池中
            while not temp_queue.empty():
                self.available_containers.put(temp_queue.get())
            
            # 检查活动容器是否超时
            for container_id, container in list(self.active_containers.items()):
                if time.time() - self.container_timestamps.get(container_id, 0) > self.config.idle_timeout:
                    logger.warning(f"Active container {container_id[:12]} has been busy for too long")
                    # 强制释放
                    try:
                        if self._stop_container(container):
                            del self.active_containers[container_id]
                            removed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to force remove container {container_id[:12]}: {str(e)}")
            
            return removed_count
    
    def _stop_container(self, container):
        """停止并移除单个容器（带超时）"""
        try:
            # 设置较短的停止超时时间（2秒）
            container.stop(timeout=2)
            container.remove()
            
            # 移除时间戳记录
            if container.id in self.container_timestamps:
                del self.container_timestamps[container.id]
            
            logger.info(f"Stopped container: {container.id[:12]}")
            return True
        except Exception as e:
            logger.warning(f"Error stopping container {container.id[:12]}: {str(e)}")
            return False
    
    def acquire_container(self, timeout=30):
        """从池中获取一个容器"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 尝试从队列中获取
                container = self.available_containers.get(timeout=1)
                
                # 检查容器是否仍然可用
                container.reload()
                if container.status == 'running':
                    with self.lock:
                        self.active_containers[container.id] = container
                        # 更新容器使用时间
                        self.container_timestamps[container.id] = time.time()
                    logger.debug(f"Acquired container: {container.id[:12]}")
                    return container
                
                # 如果容器不可用，尝试创建新的
                logger.warning(f"Container {container.id[:12]} not running, status: {container.status}")
            
            except queue.Empty:
                pass  # 继续尝试
            
            # 尝试创建新的容器
            with self.lock:
                if len(self.active_containers) + self.available_containers.qsize() < self.config.max_containers:
                    try:
                        container = self._create_container()
                        self.active_containers[container.id] = container
                        logger.info(f"Created new container for immediate use: {container.id[:12]}")
                        return container
                    except Exception:
                        pass
        
        raise TimeoutError("No containers available in pool")
    
    def release_container(self, container):
        """释放容器回池中"""
        try:
            # 检查容器状态
            container.reload()
            if container.status != 'running':
                logger.warning(f"Container {container.id[:12]} not running, status: {container.status}")
                try:
                    self._stop_container(container)
                except Exception:
                    pass
                return
            
            # 从活动容器中移除
            with self.lock:
                if container.id in self.active_containers:
                    del self.active_containers[container.id]
            
            # 放回可用队列并更新时间戳
            self.container_timestamps[container.id] = time.time()
            self.available_containers.put(container)
            logger.debug(f"Released container: {container.id[:12]}")
        
        except Exception as e:
            logger.error(f"Error releasing container {container.id[:12]}: {str(e)}")
    
    def process_config(self, config_file, output_file="out.json"):
        """处理配置文件（使用容器池）"""
        container = self.acquire_container()
        
        try:
            # 构建容器内路径
            container_config = f"{self.config.input_mount}/{config_file}"
            container_output = f"{self.config.output_mount}/{output_file}"
            
            # 执行处理命令
            cmd = f"python app.py -cmd pd -c {container_config} -o {container_output}"
            exit_code, output = container.exec_run(cmd)
            
            # 更新容器使用时间
            with self.lock:
                if container.id in self.container_timestamps:
                    self.container_timestamps[container.id] = time.time()
            
            return {
                "exit_code": exit_code,
                "output": output.decode('utf-8'),
                "config": config_file,
                "output_file": output_file
            }
        
        finally:
            self.release_container(container)
    
    def shutdown(self):
        """关闭容器池，并行清理所有容器"""
        self.running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # 收集所有需要停止的容器
        containers_to_stop = []
        with self.lock:
            # 获取所有可用容器
            while not self.available_containers.empty():
                container = self.available_containers.get()
                containers_to_stop.append(container)
            
            # 获取所有活动容器
            for container_id, container in list(self.active_containers.items()):
                containers_to_stop.append(container)
                del self.active_containers[container_id]
        
        # 使用线程池并行停止容器
        start_time = time.time()
        stopped_count = 0
        
        if containers_to_stop:
            # 使用线程池并行停止容器
            with ThreadPoolExecutor(max_workers=min(8, len(containers_to_stop))) as executor:
                # 提交所有停止任务
                future_to_container = {
                    executor.submit(self._stop_container, container): container
                    for container in containers_to_stop
                }
                
                # 等待所有任务完成（设置整体超时）
                for future in as_completed(future_to_container, timeout=10):
                    container = future_to_container[future]
                    try:
                        if future.result():
                            stopped_count += 1
                    except Exception as e:
                        logger.error(f"Error stopping container {container.id[:12]}: {str(e)}")
        
        # 清理时间戳记录
        for container in containers_to_stop:
            if container.id in self.container_timestamps:
                del self.container_timestamps[container.id]
        
        elapsed = time.time() - start_time
        logger.info(f"Stopped {stopped_count}/{len(containers_to_stop)} containers in {elapsed:.2f} seconds")
        logger.info("Container pool shutdown complete")

class JSONProcessor:
    """高级JSON处理器（使用容器池）"""
    
    def __init__(self, input_dir, output_dir, pool_config=None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 使用默认配置或自定义配置
        self.pool_config = pool_config or ContainerConfig()
        
        # 创建容器池
        self.container_pool = ContainerPool(
            config=self.pool_config,
            input_dir=input_dir,
            output_dir=output_dir
        )
    
    def process_config(self, config_file, output_file="out.json"):
        """处理单个配置文件"""
        return self.container_pool.process_config(config_file, output_file)
    
    def process_batch(self, config_files, output_files=None):
        """批量处理多个配置文件"""
        if output_files is None:
            output_files = [f"result_{i}.json" for i in range(len(config_files))]
        
        results = []
        threads = []
        lock = threading.Lock()
        
        # 使用线程池并发处理
        def process_task(idx, config_file, output_file):
            try:
                result = self.process_config(config_file, output_file)
                with lock:
                    results.append((idx, result))
            except Exception as e:
                with lock:
                    results.append((idx, {"error": str(e)}))
        
        # 创建并启动线程
        for i, (config_file, output_file) in enumerate(zip(config_files, output_files)):
            thread = threading.Thread(
                target=process_task,
                args=(i, config_file, output_file),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=120)
        
        # 按原始顺序排序结果
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    def shutdown(self):
        """关闭处理器并清理资源"""
        self.container_pool.shutdown()

if __name__ == "__main__":
    # 配置容器池
    pool_config = ContainerConfig(
        input_mount="/app/input",
        output_mount="/app/output",
        max_containers=4,  # 根据系统资源调整
        idle_timeout=180   # 3分钟空闲超时
    )
    
    # 使用示例
    engine_dir = "/Users/hejun/project/fastapi-celery/engine"
    processor = JSONProcessor(
        input_dir=f"{engine_dir}/input",
        output_dir=f"{engine_dir}/output",
        pool_config=pool_config
    )
    
    try:
        # 处理多个配置文件
        config_files = ["config1.json", "config2.json", "config3.json", "config4.json"]
        output_files = ["result1.json", "result2.json", "result3.json", "result4.json"]
        
        # 单次处理
        result = processor.process_config("config1.json", "result1.json")
        print(f"Processed {result['config']} -> {result['output_file']}")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output: {result['output']}")
        print("-" * 50)
        
        # 批量处理
        batch_results = processor.process_batch(config_files, output_files)
        
        for res in batch_results:
            if "error" in res:
                print(f"Error processing: {res['error']}")
            else:
                print(f"Processed {res['config']} -> {res['output_file']}")
                print(f"Exit code: {res['exit_code']}")
                print(f"Output: {res['output']}")
                print("-" * 50)
        
        # 压力测试
        print("Starting stress test...")
        stress_configs = [f"stress_{i}.json" for i in range(20)]
        stress_outputs = [f"stress_out_{i}.json" for i in range(20)]
        
        start_time = time.time()
        stress_results = processor.process_batch(stress_configs, stress_outputs)
        elapsed = time.time() - start_time
        
        success_count = sum(1 for res in stress_results if "exit_code" in res and res["exit_code"] == 0)
        print(f"Processed {len(stress_results)} files in {elapsed:.2f} seconds")
        print(f"Success rate: {success_count}/{len(stress_results)}")
    
    finally:
        processor.shutdown()