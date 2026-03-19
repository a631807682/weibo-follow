#!/bin/bash

# 脚本配置
PYTHON_SCRIPT="weibo_follow.py"
AVATAR_SCRIPT="weibo_avatar_downloader.py"
LOG_FILE="output.log"
USER_LIST="real_user_id_list.txt"
PYTHON_BIN="python3" # 如果是在虚拟环境，请指向 venv/bin/python3

case $1 in
    start)
        # 检查是否已在运行
        pid=$(ps -ef | grep $PYTHON_SCRIPT | grep -v grep | awk '{print $2}')
        if [ -n "$pid" ]; then
            echo "错误: 爬虫已在运行中 (PID: $pid)"
        else
            echo "正在启动爬虫..."
            nohup $PYTHON_BIN -u $PYTHON_SCRIPT > $LOG_FILE 2>&1 &
            sleep 1
            pid=$(ps -ef | grep $PYTHON_SCRIPT | grep -v grep | awk '{print $2}')
            echo "启动成功! PID: $pid"
            echo "日志输出在: $LOG_FILE"
        fi
        ;;
    stop)
        pid=$(ps -ef | grep $PYTHON_SCRIPT | grep -v grep | awk '{print $2}')
        if [ -z "$pid" ]; then
            echo "爬虫未在运行。"
        else
            echo "正在停止 PID 为 $pid 的进程..."
            kill -9 $pid
            echo "已停止。"
        fi
        ;;
    download)
        # 检查是否已在运行（防止重复启动）
        pid=$(ps -ef | grep $AVATAR_SCRIPT | grep -v grep | awk '{print $2}')
        if [ -n "$pid" ]; then
            echo "错误: 头像下载器已在运行中 (PID: $pid)"
        else
            echo "正在后台启动头像下载器..."
            # 使用 nohup 后台执行，并将日志输出到 avatar.log
            nohup $PYTHON_BIN -u $AVATAR_SCRIPT > avatar.log 2>&1 &
            sleep 1
            pid=$(ps -ef | grep $AVATAR_SCRIPT | grep -v grep | awk '{print $2}')
            echo "启动成功! PID: $pid"
            echo "查看下载进度请运行: tail -f avatar.log"
        fi
        ;;
    status)
        pid=$(ps -ef | grep $PYTHON_SCRIPT | grep -v grep | awk '{print $2}')
        if [ -n "$pid" ]; then
            echo "状态: [运行中]"
            echo "进程 ID: $pid"
        else
            echo "状态: [未运行]"
        fi
        # 统计用户数量
        if [ -f "$USER_LIST" ]; then
            count=$(wc -l < "$USER_LIST")
            echo "待处理用户数: $count"
        else
            echo "尚未找到用户列表文件。"
        fi
        ;;
    log)
        echo "正在实时显示日志 (按 Ctrl+C 退出)..."
        tail -f $LOG_FILE
        ;;
    *)
        echo "用法: sh run.sh {start|stop|download|status|log}"
        exit 1
        ;;
esac
