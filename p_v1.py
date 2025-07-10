# processor_client.py
from concurrent.futures import ThreadPoolExecutor, as_completed
import docker
import threading
import queue
import time
import os
import logging
from dataclasses import dataclass
from contextlib import contextmanager

# 配置日志
logger = logging.getLogger('ContainerPool')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

@dataclass
class ContainerConfig:
    """容器配置类"""
    input_mount: str = "/app/input"
    output_mount: str = "/app/output"
    image: str = "json-processor:latest"
    max_containers: int = 5
    idle_timeout: int = 300
    max_retries: int = 3
    health_check_timeout: int = 5

class ContainerPool:
    """容器池管理器"""
    
    def __init__(self, config: ContainerConfig, input_dir: str, output_dir: str):
        self.config = config
        self.client = docker.from_env()
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.available_containers = queue.Queue()
        self.active_containers = {}
        self.container_timestamps = {}
        self.lock = threading.Lock()
        self.running = False
        self.monitor_thread = None

    def start(self):
        """启动容器池服务"""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_pool, 
            daemon=True,
            name="ContainerPoolMonitor"
        )
        self.monitor_thread.start()
        logger.info("Container pool started")

    def _create_container(self, retry_count=0) -> docker.models.containers.Container:
        """创建并启动容器实例"""
        try:
            container = self.client.containers.run(
                image=self.config.image,
                volumes={
                    self.input_dir: {'bind': self.config.input_mount, 'mode': 'ro'},
                    self.output_dir: {'bind': self.config.output_mount, 'mode': 'rw'}
                },
                detach=True,
                auto_remove=True
            )
            
            # 等待容器健康检查
            start_time = time.time()
            while time.time() - start_time < self.config.health_check_timeout:
                container.reload()
                if container.status == 'running':
                    self.container_timestamps[container.id] = time.time()
                    logger.info(f"Container created: {container.id[:12]}")
                    return container
                time.sleep(0.2)
            
            raise RuntimeError(f"Container {container.id[:12]} failed to start within timeout")
        
        except Exception as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Container creation failed (retry {retry_count+1}/{self.config.max_retries}): {e}")
                time.sleep(1)
                return self._create_container(retry_count + 1)
            logger.error(f"Failed to create container after {self.config.max_retries} attempts: {e}")
            raise

    def _monitor_pool(self):
        """容器池监控循环"""
        while self.running:
            try:
                with self.lock:
                    # 维持最小容器数量
                    total_containers = len(self.active_containers) + self.available_containers.qsize()
                    if total_containers < self.config.max_containers:
                        try:
                            container = self._create_container()
                            self.available_containers.put(container)
                        except Exception as e:
                            logger.error(f"Failed to add container to pool: {e}")
                
                self._cleanup_idle_containers()
                time.sleep(10)
            except Exception as e:
                logger.error(f"Monitor thread error: {e}")
                time.sleep(5)

    def _cleanup_idle_containers(self):
        """清理空闲超时的容器"""
        with self.lock:
            # 处理可用容器
            temp_queue = queue.Queue()
            removed_count = 0
            
            while not self.available_containers.empty():
                container = self.available_containers.get()
                idle_time = time.time() - self.container_timestamps.get(container.id, 0)
                
                if idle_time > self.config.idle_timeout:
                    try:
                        container.stop(timeout=2)
                        logger.info(f"Removed idle container: {container.id[:12]}")
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Error removing container: {e}")
                        temp_queue.put(container)
                else:
                    temp_queue.put(container)
            
            # 将保留的容器放回队列
            while not temp_queue.empty():
                self.available_containers.put(temp_queue.get())
            
            # 检查活动容器超时
            for container_id, container in list(self.active_containers.items()):
                idle_time = time.time() - self.container_timestamps.get(container_id, 0)
                if idle_time > self.config.idle_timeout:
                    logger.warning(f"Force releasing long-running container: {container_id[:12]}")
                    self._release_container(container_id)
            
            return removed_count

    @contextmanager
    def acquire(self, timeout=30):
        """上下文管理器获取容器资源"""
        container = self._acquire_container(timeout)
        try:
            yield container
        finally:
            self._release_container(container.id)

    def _acquire_container(self, timeout=30) -> docker.models.containers.Container:
        """获取容器实例"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 尝试从队列获取
                container = self.available_containers.get(timeout=1)
                container.reload()
                
                if container.status == 'running':
                    with self.lock:
                        self.active_containers[container.id] = container
                        self.container_timestamps[container.id] = time.time()
                    logger.debug(f"Acquired container: {container.id[:12]}")
                    return container
                
                logger.warning(f"Container {container.id[:12]} not running (status: {container.status})")
            except queue.Empty:
                pass
            
            # 尝试创建新容器
            with self.lock:
                if len(self.active_containers) < self.config.max_containers:
                    try:
                        container = self._create_container()
                        self.active_containers[container.id] = container
                        logger.info(f"Created new container for immediate use: {container.id[:12]}")
                        return container
                    except Exception as e:
                        logger.error(f"Failed to create container: {e}")
        
        raise TimeoutError("No containers available in pool")

    def _release_container(self, container_id: str):
        """释放容器回池中"""
        with self.lock:
            if container_id not in self.active_containers:
                return
                
            container = self.active_containers.pop(container_id)
        
        try:
            container.reload()
            if container.status == 'running':
                self.container_timestamps[container.id] = time.time()
                self.available_containers.put(container)
                logger.debug(f"Released container: {container.id[:12]}")
            else:
                logger.warning(f"Container {container.id[:12]} not running (status: {container.status})")
                try:
                    container.stop(timeout=2)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error releasing container: {e}")

    def shutdown(self):
        """关闭容器池"""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        containers_to_stop = []
        with self.lock:
            while not self.available_containers.empty():
                containers_to_stop.append(self.available_containers.get())
            containers_to_stop.extend(self.active_containers.values())
            self.active_containers.clear()
        
        # 并行停止容器
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=min(8, len(containers_to_stop))) as executor:
            futures = [executor.submit(self._stop_container, c) for c in containers_to_stop]
            for future in as_completed(futures, timeout=10):
                future.result()
        
        logger.info(f"Shutdown completed in {time.time()-start_time:.2f}s")

    def _stop_container(self, container):
        """停止单个容器"""
        try:
            container.stop(timeout=2)
            logger.info(f"Stopped container: {container.id[:12]}")
            return True
        except Exception as e:
            logger.warning(f"Error stopping container: {e}")
            return False

class JSONProcessor:
    """JSON处理器"""
    
    def __init__(self, input_dir, output_dir, pool_config=None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.pool_config = pool_config or ContainerConfig()
        self.container_pool = ContainerPool(
            config=self.pool_config,
            input_dir=input_dir,
            output_dir=output_dir
        )
        self.container_pool.start()

    def process_config(self, config_file, output_file="out.json"):
        """处理单个配置文件"""
        with self.container_pool.acquire() as container:
            container_config = f"{self.container_pool.config.input_mount}/{config_file}"
            container_output = f"{self.container_pool.config.output_mount}/{output_file}"
            
            cmd = f"python app.py -cmd pd -c {container_config} -o {container_output}"
            exit_code, output = container.exec_run(cmd)
            
            return {
                "exit_code": exit_code,
                "output": output.decode('utf-8'),
                "config": config_file,
                "output_file": output_file
            }

    def process_batch(self, config_files, output_files=None):
        """批量处理配置文件"""
        output_files = output_files or [f"result_{i}.json" for i in range(len(config_files))]
        
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.process_config, cfg, out): (cfg, out)
                for cfg, out in zip(config_files, output_files)
            }
            
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    cfg, out = futures[future]
                    results.append({
                        "error": str(e),
                        "config": cfg,
                        "output_file": out
                    })
            return results

    def shutdown(self):
        """关闭处理器"""
        self.container_pool.shutdown()

# 示例使用代码
if __name__ == "__main__":
    # 配置容器池
    pool_config = ContainerConfig(
        input_mount="/app/input",
        output_mount="/app/output",
        max_containers=4,
        idle_timeout=180
    )
    
    # processor = JSONProcessor(
    #     input_dir="/path/to/input",
    #     output_dir="/path/to/output",
    #     pool_config=pool_config
    # )
    engine_dir = "/Users/hejun/project/fastapi-celery/engine"
    processor = JSONProcessor(
        input_dir=f"{engine_dir}/input",
        output_dir=f"{engine_dir}/output",
        pool_config=pool_config
    )
    
    try:
        # 单文件处理示例
        result = processor.process_config("config1.json", "result1.json")
        print(f"Processed: {result['config']} -> {result['output_file']}")
        
        # 批量处理示例
        configs = [f"config_{i}.json" for i in range(10)]
        results = processor.process_batch(configs)
        
        for res in results:
            if "error" in res:
                print(f"Failed: {res['config']} - {res['error']}")
            else:
                print(f"Success: {res['config']} -> {res['output_file']}")
    
    finally:
        processor.shutdown()