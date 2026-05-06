# 3LM-setup-wizard

## 目次/INDEX
[日本語](#日本語)|[English](#english)

## 日本語

### 概要
3LM-setup-wizardは、ローカル環境でLLM（Large Language Model）を動作させるための「3LM環境（Local LLM推論環境）」を自動で構築するためのセットアップツールです。
特にGGUF形式のモデルを高速に動作させる `llama-cpp-python` のビルドと設定を、ユーザーのハードウェアに合わせて最適化します。

### 主な機能
*   **ハードウェア自動診断**: システムのCPU、GPU（NVIDIA CUDA / AMD・Intel Vulkan / Apple Silicon Metal）を自動で判別し、最適なビルドオプションを提案します。
*   **仮想環境（venv）管理**: システムのPython環境を汚染しないよう、カレントディレクトリへの仮想環境作成をサポートします。
*   **バイリンガル対応**: 画面上のガイダンスはすべて日本語と英語で併記されます。
*   **スモークテスト機能**: セットアップ完了後、軽量なLLMモデルを自動でダウンロードし、実際に推論が可能かを確認するテストを実行できます。
*   **ログ・スナップショット保存**: 実行時の詳細なログと、構築された環境の構成情報をJSON形式で保存します。

### 使用方法
1.  本リポジトリをクローンまたはダウンロードします。
2.  ターミナル（またはPowerShell）を開き、本ディレクトリに移動します。
3.  以下のコマンドを実行します。
    ```bash
    python setup_wizard.py
    ```
4.  画面上の指示に従って番号を選択してください。

---

## English

### Overview
3LM-setup-wizard is an automated setup tool designed to build a "3LM Environment" (Local LLM inference environment).
It optimizes the build and configuration of `llama-cpp-python` to run GGUF format models efficiently based on the user's hardware.

### Key Features
*   **Auto-Hardware Diagnostics**: Automatically detects CPU and GPU (NVIDIA CUDA / AMD & Intel Vulkan / Apple Silicon Metal) to suggest the best build options.
*   **Virtual Environment (venv) Management**: Supports creating a virtual environment in the current directory to avoid polluting the system Python.
*   **Bilingual Interface**: All on-screen guidance is provided in both Japanese and English.
*   **Smoke Test**: After setup, it can automatically download a lightweight LLM model and perform an inference test to verify the environment.
*   **Logging & Environment Snapshots**: Saves detailed execution logs and environment configuration details in JSON format.

### How to Use
1.  Clone or download this repository.
2.  Open a terminal (or PowerShell) and navigate to this directory.
3.  Run the following command:
    ```bash
    python setup_wizard.py
    ```
4.  Follow the on-screen instructions and select the appropriate number.