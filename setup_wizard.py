import os
import sys
import platform
import subprocess
import shutil
import logging
import json
import urllib.request

# --- Constants ---
MAX_SAFE_GPU_LAYERS = 20  # Safe default for testing on ~4GB VRAM

# --- Windows ANSI Color Fix ---
if platform.system() == "Windows":
    os.system("")

# --- ANSI Colors (TUI-lite) ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# --- Logging Setup ---
logging.basicConfig(
    filename='setup.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def print_color(text, color):
    print(f"{color}{text}{Colors.RESET}")

def log_and_print(text, color=Colors.RESET, level=logging.INFO):
    print_color(text, color)
    clean_text = text.replace('\n', ' ').strip()
    if level == logging.ERROR:
        logging.error(clean_text)
    elif level == logging.WARNING:
        logging.warning(clean_text)
    else:
        logging.info(clean_text)

def run_command(cmd, env=None, capture_output=False):
    """Execute command. Returns True on success, False on failure."""
    cmd_str = ' '.join(cmd)
    logging.debug(f"Executing: {cmd_str}")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.debug(f"Stdout: {result.stdout.decode('utf-8', 'replace')}")
            return True
        else:
            subprocess.run(cmd, env=env, check=True)
            return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', 'replace') if capture_output and e.stderr else f"Exit code: {e.returncode}"
        log_and_print(f"\n[Error / エラー] Command failed / コマンドの実行に失敗しました。", Colors.RED, logging.ERROR)
        log_and_print(f"Command: {cmd_str}", Colors.RED, logging.ERROR)
        if capture_output and e.stderr:
            log_and_print(f"[Error Details / エラー詳細]\n{error_msg}", Colors.YELLOW, logging.ERROR)
        return False

def check_venv():
    """Check if running inside a virtual environment and offer to create one."""
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        log_and_print("\n[Warning / 警告] Not running in a virtual environment. / 仮想環境（venv等）の外で実行されています。", Colors.YELLOW, logging.WARNING)
        print("This may pollute your system Python. / システムのPython環境を汚染する可能性があります。")
        
        ans_create = input(f"{Colors.CYAN}Create a new 'venv' in the current directory? / カレントディレクトリにvenvを作成しますか？ (y/N): {Colors.RESET}").strip().lower()
        if ans_create == 'y':
            log_and_print("Creating venv... / venvを作成中...", Colors.BLUE)
            try:
                subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
                log_and_print("\n[Success / 成功] venv created successfully. / venvの作成が完了しました。", Colors.GREEN)
                print_color("Please activate it and run this script again: / 以下のコマンドで有効化してから、再度スクリプトを実行してください:", Colors.BOLD)
                if platform.system() == "Windows":
                    print("  .\\venv\\Scripts\\activate")
                else:
                    print("  source venv/bin/activate")
                print("  python setup_wizard.py")
                sys.exit(0)
            except subprocess.CalledProcessError:
                log_and_print("[Error / エラー] Failed to create venv. / venvの作成に失敗しました。", Colors.RED, logging.ERROR)
                sys.exit(1)
        
        ans_cont = input(f"{Colors.YELLOW}Continue anyway? / このまま続行しますか？ (y/N): {Colors.RESET}").strip().lower()
        if ans_cont != 'y':
            log_and_print("Aborted. / 処理を中断しました。", Colors.RED)
            sys.exit(1)

def get_recommended_backend():
    """Auto-detect the best backend for the system."""
    system = platform.system()
    machine = platform.machine().lower()
    
    if system == "Darwin" and machine == "arm64":
        return "4"
    
    if shutil.which("nvcc"):
        if system == "Windows" and shutil.which("cl") is None:
            pass
        else:
            return "2"
            
    if shutil.which("vulkaninfo"):
        return "3"
        
    return "1"

def check_prerequisites(choice):
    """Check required build tools for the selected option."""
    missing_tools = []

    if choice in ["2", "3", "4"] and shutil.which("cmake") is None:
        missing_tools.append("CMake (Required for GPU build / GPU対応ビルドに必須)")

    if choice == "2":
        if shutil.which("nvcc") is None:
            missing_tools.append("CUDA Toolkit (nvcc)")
        if platform.system() == "Windows" and shutil.which("cl") is None:
            missing_tools.append("MSVC Build Tools (cl.exe - Use Developer PowerShell / Developer PowerShell 等を使用してください)")
            
    elif choice == "3":
        if shutil.which("vulkaninfo") is None:
            log_and_print("\n[Notice / 通知] 'vulkaninfo' not found. Vulkan might not work properly. / 'vulkaninfo'が見つかりません。Vulkanが正常に動作しない可能性があります。", Colors.YELLOW, logging.WARNING)
            
    elif choice == "4":
        if not run_command(["xcode-select", "-p"], capture_output=True):
            missing_tools.append("Xcode Command Line Tools")
    
    if missing_tools:
        log_and_print("\n[Error / エラー] Missing required tools. Please install them and try again: / 以下の必要なツールが見つかりません。インストールしてから再実行してください:", Colors.RED, logging.ERROR)
        for tool in missing_tools:
            print(f"  - {tool}")
        return False
    return True

def install_requirements():
    """Install base requirements from requirements.txt."""
    if not os.path.exists("requirements.txt"):
        log_and_print("\nrequirements.txt not found. Skipping base packages. / requirements.txtが見つかりません。ベースパッケージのインストールをスキップします。", Colors.YELLOW)
        return True

    log_and_print("\nInstalling base packages from requirements.txt... / ベースパッケージのインストールを開始します...", Colors.BLUE)
    return run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def install_llama_cpp(choice):
    """Install llama-cpp-python based on the selected option."""
    env = os.environ.copy()
    base_cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--upgrade", "--force-reinstall", "--no-cache-dir"]
    cmake_args = ""
    backend_name = "CPU"
    
    if choice == "1":
        log_and_print("\nInstalling Standard CPU version... / 標準のCPU版をインストールします。", Colors.CYAN)
        cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--upgrade"]
        
    elif choice == "2":
        backend_name = "CUDA"
        log_and_print("\nInstalling NVIDIA GPU (CUDA) version... / NVIDIA GPU (CUDA) 版をインストールします。", Colors.CYAN)
        cmake_args = "-DGGML_CUDA=on"
        if platform.system() == "Windows":
            cmake_args += " -GNinja"
        cmd = base_cmd + ["--no-binary", "llama-cpp-python"]

    elif choice == "3":
        backend_name = "Vulkan"
        log_and_print("\nInstalling AMD/Intel GPU (Vulkan) version... / AMD/Intel GPU (Vulkan) 版をインストールします。", Colors.CYAN)
        cmake_args = "-DGGML_VULKAN=on"
        if platform.system() == "Windows":
            cmake_args += " -GNinja"
        cmd = base_cmd + ["--no-binary", "llama-cpp-python"]
        
    elif choice == "4":
        backend_name = "Metal"
        log_and_print("\nInstalling macOS (Metal) version... / macOS (Metal) 版をインストールします。", Colors.CYAN)
        cmake_args = "-DGGML_METAL=on"
        cmd = base_cmd + ["--no-binary", "llama-cpp-python"]
        
    else:
        return False, None, None

    if cmake_args:
        env["CMAKE_ARGS"] = cmake_args
        logging.info(f"Using CMAKE_ARGS: {cmake_args}")

    log_and_print("Executing installation. This may take a few minutes... / インストールを実行中です。完了まで数分かかる場合があります...", Colors.BOLD)
    success = run_command(cmd, env=env)
    return success, backend_name, cmake_args

def validate_installation():
    """Test the installation by importing Llama."""
    log_and_print("\nValidating llama-cpp-python installation... / インストールされた llama-cpp-python の動作確認を行っています...", Colors.BLUE)
    success = run_command([sys.executable, "-c", "from llama_cpp import Llama"], capture_output=True)
    if not success:
        log_and_print("\n[Error / エラー] Installation finished, but runtime test failed. / インストール処理は完了しましたが、ライブラリの実行テストに失敗しました。", Colors.RED, logging.ERROR)
        print("There might be an incompatibility with system libraries (CUDA, Vulkan, etc.). / システムのライブラリ（CUDAやVulkan等）との間に不整合がある可能性があります。")
        return False
    log_and_print("[Success / 成功] Validation passed. / 動作確認をパスしました。", Colors.GREEN)
    return True

def run_smoke_test(backend_name):
    """Download a small model and run inline inference to guarantee it works."""
    ans = input(f"\n{Colors.CYAN}Do you want to run a quick Smoke Test with a small model? / 軽量モデルをダウンロードして推論テストを行いますか？ (y/N): {Colors.RESET}").strip().lower()
    if ans != 'y':
        return

    model_url = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    model_name = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    
    if os.path.exists(model_name) and os.path.getsize(model_name) > 0:
        log_and_print(f"\nModel {model_name} already exists. Skipping download. / モデルファイルが既に存在するため、ダウンロードをスキップします。", Colors.GREEN)
    else:
        log_and_print(f"\nDownloading test model ({model_name})... / テスト用モデルをダウンロードしています...", Colors.BLUE)
        temp_name = model_name + ".tmp"
        
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, block_num * block_size * 100 / total_size)
                print(f'\r{Colors.BLUE}Downloading / ダウンロード中: {percent:.1f}%{Colors.RESET}', end='')
            else:
                downloaded = (block_num * block_size) / (1024 * 1024)
                print(f'\r{Colors.BLUE}Downloading / ダウンロード中: {downloaded:.1f} MB{Colors.RESET}', end='')

        try:
            urllib.request.urlretrieve(model_url, temp_name, reporthook)
            print() # Print a newline explicitly after the download completes
            os.replace(temp_name, model_name)
            log_and_print("Download complete. / ダウンロード完了。", Colors.GREEN)
        except Exception as e:
            print()
            log_and_print(f"\n[Error / エラー] Download failed: {e} / ダウンロードに失敗しました。", Colors.RED, logging.ERROR)
            if os.path.exists(temp_name):
                os.remove(temp_name)
            return

    gpu_layers = MAX_SAFE_GPU_LAYERS if backend_name in ["CUDA", "Vulkan", "Metal"] else 0
    
    test_script = f"""
import sys
try:
    from llama_cpp import Llama
    print('\\nLoading model with {gpu_layers} GPU layers... / モデルを読み込んでいます...')
    try:
        llm = Llama(model_path="{model_name}", n_gpu_layers={gpu_layers}, verbose=False)
    except Exception as e_gpu:
        print(f'\\n[Warning / 警告] GPU loading failed, falling back to CPU... / GPUでの読み込みに失敗したため、CPUにフォールバックします。Error: {{e_gpu}}')
        llm = Llama(model_path="{model_name}", n_gpu_layers=0, verbose=False)
        
    print('Generating text... / 推論を実行しています...')
    output = llm.create_chat_completion(
        messages=[{{"role": "user", "content": "Say 'Hello, setup is complete!' and nothing else."}}],
        max_tokens=20
    )
    print('\\n[AI Response / AIの応答] ' + output['choices'][0]['message']['content'].strip())
except Exception as e:
    print(f'\\n[Inference Error / 推論エラー] {{e}}')
    sys.exit(1)
"""
    log_and_print("Running inline inference... / インラインで推論テストを実行しています...", Colors.BLUE)
    success = run_command([sys.executable, "-c", test_script])
    
    if success:
        log_and_print("\n[Success / 成功] Smoke test passed! The environment is ready. / 推論テスト成功！環境は完全に動作しています。", Colors.GREEN)
    else:
        log_and_print("\n[Error / エラー] Smoke test failed. / 推論テストに失敗しました。", Colors.RED)
        
    keep = input(f"\n{Colors.YELLOW}Keep the downloaded model file? / ダウンロードしたモデルファイルを保持しますか？ (Y/n): {Colors.RESET}").strip().lower()
    if keep == 'n' and os.path.exists(model_name):
        os.remove(model_name)
        log_and_print("Model deleted. / モデルを削除しました。")

def save_snapshot(backend_name, cmake_args):
    """Save environment configuration to JSON."""
    snapshot = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "backend": backend_name,
        "cmake_args": cmake_args,
        "llama_cpp_installed": True
    }
    try:
        with open("3lm_env_snapshot.json", "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=4)
        logging.info("Saved environment snapshot to 3lm_env_snapshot.json")
    except Exception as e:
        logging.error(f"Failed to save snapshot: {e}")

def get_available_options():
    """Generate available options based on OS and Architecture."""
    system = platform.system()
    machine = platform.machine().lower()
    
    options = {"1": "Standard CPU (Stable/Recommended) / 標準インストール（CPUのみ / 安定・推奨）"}
    
    if system in ["Windows", "Linux"]:
        options["2"] = "NVIDIA GPU (CUDA) *Requires CUDA Toolkit / ※要 CUDA Toolkit"
        options["3"] = "AMD/Intel GPU (Vulkan) *Requires Vulkan Drivers / ※要 Vulkan対応ドライバ"
    elif system == "Darwin":
        if machine == "arm64":
            options["4"] = "macOS (Metal) *Requires Xcode CLT / ※要 Xcode Command Line Tools"
            
    return options

def main():
    log_and_print("--- 3LM (GGUF) Environment Setup Wizard / 汎用3LM環境セットアップウィザード ---", Colors.HEADER)
    
    check_venv()
    
    options = get_available_options()
    recommended = get_recommended_backend()
    
    print_color("\nPlease select your hardware environment: / ご使用のハードウェア環境に合わせて、該当する番号を選択してください。", Colors.BOLD)
    print_color(f"0: Auto Detect (Recommended: {recommended}) / 自動判定（推奨: {recommended}）", Colors.GREEN)
    for key, desc in options.items():
        print(f"{key}: {desc}")
    
    choice = input(f"\nEnter number / 番号を入力してください: {Colors.RESET}").strip()
    
    if choice == "0":
        choice = recommended
        log_and_print(f"Auto-selected backend: {choice} / バックエンドを自動選択しました: {choice}", Colors.GREEN)
        
    if choice not in options:
        log_and_print("\n[Exit / 終了] Invalid selection. Exiting. / 正しい番号が入力されなかったため、処理を終了します。", Colors.RED)
        sys.exit(1)

    if not check_prerequisites(choice):
        sys.exit(1)

    if platform.system() == "Windows" and choice in ["2", "3"]:
        log_and_print("\nInstalling build tool (ninja)... / ビルドツール(ninja)のインストールを実行しています...", Colors.BLUE)
        if not run_command([sys.executable, "-m", "pip", "install", "ninja"]):
            sys.exit(1)
    
    if not install_requirements():
        sys.exit(1)
        
    success, backend_name, cmake_args = install_llama_cpp(choice)
    if not success:
        sys.exit(1)
        
    if not validate_installation():
        sys.exit(1)
        
    save_snapshot(backend_name, cmake_args)
    
    run_smoke_test(backend_name)
    
    log_and_print("\n[Success / 成功] Setup wizard completed successfully! / セットアップウィザードが正常に完了しました！", Colors.HEADER)
    log_and_print("Check 'setup.log' and '3lm_env_snapshot.json' for details. / 詳細は 'setup.log' と '3lm_env_snapshot.json' を確認してください。")

if __name__ == "__main__":
    main()