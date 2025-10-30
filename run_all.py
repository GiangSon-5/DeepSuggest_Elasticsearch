import argparse
import subprocess
import sys
import os
import time
import requests
from requests.exceptions import ConnectionError
from dotenv import load_dotenv
import signal

load_dotenv()

ES_HOST_URL = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
PYTHON_EXE = sys.executable if sys.executable else "python"
SCRIPT_PREPROCESS = "scripts/preprocess_csv.py"
SCRIPT_EMBED = "scripts/embed_to_json.py"
SCRIPT_IMPORT = "scripts/import_to_elasticsearch.py"
EMBED_CACHE_FILE = os.getenv("EMBEDDED_JSON_FILE", "data/mock_products_with_embedding.json")

def run_command(command, description, exit_on_error=True):
    print(f"\n🚀 [ĐANG CHẠY] {description}...")
    print(f"   Lệnh: {' '.join(command)}")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding='utf-8', env=env
        )
        if result.stdout: print("   [OUTPUT]:\n---\n" + result.stdout.strip() + "\n---")
        if result.stderr:
            stderr_output = result.stderr.strip()
            if stderr_output and "the attribute `version` is obsolete" not in stderr_output:
                print(f"   [LOG Phụ/Cảnh báo]: {stderr_output}")
        print(f"✅ [THÀNH CÔNG] {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ [LỖI NGHIÊM TRỌNG] {description} thất bại.")
        print(f"   Lệnh: {' '.join(e.cmd)}")
        print(f"   Exit Code: {e.returncode}")
        if e.stdout: print(f"   STDOUT: {e.stdout.strip()}")
        if e.stderr: print(f"   STDERR: {e.stderr.strip()}")
        if exit_on_error: raise
        else: return False
    except FileNotFoundError:
         print(f"❌ [LỖI] Không tìm thấy lệnh: {command[0]}.")
         if exit_on_error: raise
         else: return False

def wait_for_elasticsearch(url, timeout):
    print(f"⏱️ [ĐANG CHỜ] Elasticsearch tại {url} (timeout: {timeout}s)...")
    start_time = time.time()
    while True:
        try:
            response = requests.get(url + "/_cluster/health?wait_for_status=yellow&timeout=5s", timeout=10)
            response.raise_for_status() # Check for HTTP errors
            health = response.json().get('status')
            if health in ('yellow', 'green'):
                print(f"\n✅ [SẴN SÀNG] Elasticsearch ({health}) sau {time.time() - start_time:.2f}s!")
                return True
            else:
                 print(f" ({health})", end="", flush=True)
        except ConnectionError: print("c", end="", flush=True)
        except requests.Timeout: print("t", end="", flush=True)
        except requests.RequestException as e: print(f" E({e.response.status_code if e.response else 'N/A'})", end="", flush=True) # Print HTTP error code
        except Exception as e: print(f"\n   ⚠️ Lỗi polling ES: {e}")

        if time.time() - start_time > timeout:
            print(f"\n❌ [LỖI] Hết {timeout}s chờ Elasticsearch.")
            return False

        print(".", end="", flush=True)
        time.sleep(3)

def setup_argparse():
    parser = argparse.ArgumentParser(description="Script điều phối tổng.", formatter_class=argparse.RawTextHelpFormatter)
    docker_group = parser.add_argument_group('Docker')
    docker_group.add_argument("--no-docker", action="store_true", help="Bỏ qua các lệnh Docker.")
    docker_group.add_argument("--stop-after", choices=['down', 'down-v'], nargs='?', const='down', help="Chạy 'docker-compose down [-v]' sau khi xong.")
    docker_group.add_argument("--timeout-es", type=int, default=180, help="Thời gian chờ ES (giây).")
    docker_group.add_argument("--prune-docker", action="store_true", help="Chạy 'docker system prune -a -f' sau khi xong.")

    pipeline_group = parser.add_argument_group('Pipeline')
    pipeline_group.add_argument("--skip-preprocess", action="store_true", help="Bỏ qua preprocess.")
    pipeline_group.add_argument("--only-preprocess", action="store_true", help="Chỉ chạy preprocess.")
    pipeline_group.add_argument("--skip-embed", action="store_true", help="Bỏ qua embedding.")
    pipeline_group.add_argument("--only-embed", action="store_true", help="Chỉ chạy embedding.")
    pipeline_group.add_argument("--force-embed", action="store_true", help="Ép tạo lại embedding.")
    return parser.parse_args()

def main():
    args = setup_argparse()
    start_pipeline_time = time.time()
    print("="*50 + "\n--- 🚀 BẮT ĐẦU QUY TRÌNH ORCHESTRATOR ---\n" + "="*50)

    try:
        if args.force_embed:
            print("🔥 [FORCE-EMBED] Đang xóa cache embedding...")
            if os.path.exists(EMBED_CACHE_FILE):
                try:
                    os.remove(EMBED_CACHE_FILE)
                    print(f"   ✅ Đã xóa: {EMBED_CACHE_FILE}")
                except Exception as e: print(f"   ⚠️ Lỗi xóa cache: {e}")
            else: print(f"   ℹ️ Cache không tồn tại: {EMBED_CACHE_FILE}")

        if not args.no_docker:
            print("\n--- Bước 1: Khởi động Docker ---")
            if not run_command(["docker-compose", "build"], "🏗️  Build Docker images"): raise Exception("Build lỗi.")
            if not run_command(["docker-compose", "up", "-d"], "🐳 Khởi động Docker containers"): raise Exception("Up lỗi.")
            if not wait_for_elasticsearch(ES_HOST_URL, args.timeout_es):
                 print("❌ ES không sẵn sàng. Kiểm tra logs: docker-compose logs elasticsearch")
                 sys.exit(1)
        else:
            print("🚫 [BỎ QUA] Docker.")
            print("   Kiểm tra kết nối ES...")
            try: requests.get(ES_HOST_URL, timeout=5).raise_for_status()
            except Exception as e: print(f"   ⚠️ Lỗi kết nối ES: {e}")

        print("\n--- Bước 2: Chạy Data Pipeline ---")
        if not args.skip_preprocess:
            if not run_command([PYTHON_EXE, SCRIPT_PREPROCESS], "📑 (1/3) Preprocess"): raise Exception("Preprocess lỗi.")
        else: print("🚫 [BỎ QUA] Preprocess.")
        if args.only_preprocess: sys.exit(0) # Thoát sớm

        if not args.skip_embed:
            if not run_command([PYTHON_EXE, SCRIPT_EMBED], "🧠 (2/3) Embedding"): raise Exception("Embedding lỗi.")
        else: print("🚫 [BỎ QUA] Embedding.")
        if args.only_embed: sys.exit(0) # Thoát sớm

        print("⏩ (3/3) Chạy Import...")
        if not run_command([PYTHON_EXE, SCRIPT_IMPORT], "🚚 (3/3) Import to ES"): raise Exception("Import lỗi.")

        print("\n" + "="*50 + "\n--- 🎉 QUY TRÌNH HOÀN TẤT THÀNH CÔNG ---\n" + "="*50)

    except (Exception, KeyboardInterrupt) as e:
        print("\n" + "="*50 + f"\n--- ❌ LỖI: {type(e).__name__} ---")
        if not isinstance(e, KeyboardInterrupt): print(f"   Lý do: {e}")
        else: print("   Lý do: Người dùng hủy (Ctrl+C).")
        print("="*50)
        # Không thoát, để finally chạy

    finally:
        print("\n" + "="*50 + "\n--- 🧹 DỌN DẸP (NẾU CẦN) ---\n" + "="*50)
        if args.stop_after and not args.no_docker:
            print(f"⏳ Yêu cầu tắt Docker (--stop-after {args.stop_after})...")
            cmd = ["docker-compose", "down"] + (["-v"] if args.stop_after == "down-v" else [])
            run_command(cmd, "🛑 Tắt Docker", exit_on_error=False)
        if args.prune_docker:
             print("⏳ Yêu cầu dọn dẹp Docker (--prune-docker)...")
             run_command(["docker", "system", "prune", "-a", "-f"], "🗑️ Dọn dẹp Docker", exit_on_error=False)
        print("--- ✅ DỌN DẸP HOÀN TẤT ---")
        print_total_time(start_pipeline_time)
        print("="*50)

def print_total_time(start_time):
    print(f"⏱️ Tổng thời gian: {time.time() - start_time:.2f} giây")

if __name__ == "__main__":
    main()