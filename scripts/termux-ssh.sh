#!/data/data/com.termux/files/usr/bin/bash
# A temporary, public-key-only SSH server. No embedded user key or device address.
set -euo pipefail
umask 077

fail() { printf '失败：%s\n' "$*" >&2; exit 1; }
[ -n "${PREFIX:-}" ] && command -v pkg >/dev/null 2>&1 || fail '请在电视 Termux 中执行。'
task_dir="$HOME/.local/share/tv-aerial-ssh"
config_file="$task_dir/sshd_config"
pid_file="$task_dir/sshd.pid"

is_our_server() {
    [ -r "$pid_file" ] || return 1
    task_pid=$(cat "$pid_file")
    case "$task_pid" in ''|*[!0-9]*) return 1 ;; esac
    kill -0 "$task_pid" 2>/dev/null || return 1
    [ -r "/proc/$task_pid/cmdline" ] || return 1
    tr '\000' '\n' < "/proc/$task_pid/cmdline" | grep -Fq "$config_file"
}

if [ "${1:-}" = stop ]; then
    if is_our_server; then
        kill "$task_pid"
        printf '已停止本脚本的 SSH 监听；已有会话可能仍存在，公钥授权未删除。\n'
    else
        printf '未确认本脚本的监听进程，不停止其他服务。\n'
    fi
    exit 0
fi

[ "$#" -eq 1 ] || fail '用法：bash termux-ssh.sh 公钥文件.pub；停止：bash termux-ssh.sh stop'
pub_file="$1"
[ -f "$pub_file" ] || fail '找不到公钥文件。'
[ "$(/system/bin/id -u)" != 0 ] || fail '请以普通 Termux 应用身份执行，不要以 root 启动 SSH。'
sdk=$(/system/bin/getprop ro.build.version.sdk)
case "$sdk" in ''|*[!0-9]*) fail '无法读取 Android SDK。' ;; esac
[ "$sdk" -ge 24 ] || fail '此脚本使用当前 Termux 软件源，要求 Android 7+。'

printf '[1/3] 准备 OpenSSH（首次安装会联网）\n'
if ! command -v sshd >/dev/null 2>&1 || ! command -v ssh-keygen >/dev/null 2>&1; then
    pkg update -y
    DEBIAN_FRONTEND=noninteractive pkg install -y openssh
fi
public_key=$(tr -d '\r' < "$pub_file")
[ -n "$public_key" ] || fail '公钥为空。'
case "$public_key" in *$'\n'*) fail '只接受单行公钥，不接受私钥或多行授权规则。' ;; esac
case "$public_key" in ssh-ed25519\ *|ssh-rsa\ *|ecdsa-sha2-nistp256\ *) ;; *) fail '不支持的公钥格式；不要传入私钥。' ;; esac
ssh-keygen -lf "$pub_file" >/dev/null || fail '公钥校验失败。'

printf '[2/3] 保留已有公钥并追加本次公钥\n'
mkdir -p "$task_dir" "$HOME/.ssh"
chmod 700 "$task_dir" "$HOME/.ssh"
auth_file="$HOME/.ssh/authorized_keys"
touch "$auth_file"
chmod 600 "$auth_file"
if ! grep -Fqx "$public_key" "$auth_file"; then
    [ ! -s "$auth_file" ] || printf '\n' >> "$auth_file"
    printf '%s\n' "$public_key" >> "$auth_file"
fi

printf '[3/3] 启动 8022 端口的临时 SSH\n'
if ! is_our_server; then
    if [ ! -s "$task_dir/host_ed25519" ]; then
        ssh-keygen -q -t ed25519 -N '' -f "$task_dir/host_ed25519"
    fi
    cat > "$config_file" <<EOF
Port 8022
AddressFamily inet
HostKey $task_dir/host_ed25519
PidFile $pid_file
AuthorizedKeysFile $auth_file
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
Subsystem sftp internal-sftp
EOF
    sshd -t -f "$config_file"
    sshd -f "$config_file" -E "$task_dir/sshd.log"
    sleep 1
    is_our_server || fail '未确认 SSH 已启动；查看该目录 sshd.log，可能端口已被占用。'
fi
printf '用户名：%s\n端口：8022\n' "$(whoami)"
printf '主机公钥指纹（首次从电脑连接时核对）：\n'
ssh-keygen -lf "$task_dir/host_ed25519.pub"
printf '请从电视网络设置获取 IP。未启用 ADB、未提权、未设置开机自启。\n'
