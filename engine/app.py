# app.py
import argparse
import json
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Process JSON configuration file.')
    parser.add_argument('-cmd', required=True, choices=['pd'], help='Specify the command (must be "pd")')
    parser.add_argument('-c', '--config', required=True, help='Path to input JSON config file')
    parser.add_argument('-o', '--output', default='out.json', help='Output JSON file path (default: out.json)')
    
    args = parser.parse_args()
    
    try:
        # 读取输入的JSON文件
        with open(args.config, 'r') as f:
            data = json.load(f)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 将数据写入输出文件
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"Success: Processed {args.config} -> {args.output}")
        return 0
    
    except FileNotFoundError:
        print(f"Error: Config file not found at {args.config}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {args.config}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"Error: Permission denied for {args.output}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        return 4

if __name__ == '__main__':
    sys.exit(main())