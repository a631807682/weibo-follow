#!/bin/bash

# 脚本配置
PYTHON_SCRIPT="weibo_follow.py"
LOG_FILE="output.log"
DATA_FILE="weibo_follow_data.csv"
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
    status)
        pid=$(ps -ef | grep $PYTHON_SCRIPT | grep -v grep | awk '{print $2}')
        if [ -n "$pid" ]; then
            echo "状态: [运行中]"
            echo "进程 ID: $pid"
        else
            echo "状态: [未运行]"
        fi
        # 统计数据量
        if [ -f "$DATA_FILE" ]; then
            count=$(wc -l < "$DATA_FILE")
            echo "已抓取用户数: $((count-1))"
        else
            echo "尚未创建数据文件。"
        fi
        ;;
    log)
        echo "正在实时显示日志 (按 Ctrl+C 退出)..."
        tail -f $LOG_FILE
        ;;
    *)
        echo "用法: sh run.sh {start|stop|status|log}"
        exit 1
        ;;
esac
