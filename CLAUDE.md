# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个网络监控工具，用于跟踪目标设备（通过IP或MAC地址识别）的在线/离线状态，并记录带有持续时间的事件。该工具还支持状态变化的Slack通知，并可以在Docker容器中运行。

## 主要组件

1. `monitor.py` - 实现NetworkMonitor类的主要监控脚本
2. `config.yaml` - 目标设备和监控设置的配置文件
3. `Dockerfile` 和 `docker-compose.yaml` - Docker部署配置
4. `requirements.txt` - Python依赖项 (PyYAML, requests)

## 架构

NetworkMonitor类是核心组件，它：
- 从YAML文件读取配置
- 使用ping（针对IP）或ARP表检查（针对MAC）来监控目标设备
- 通过可配置的阈值跟踪状态变化
- 将事件记录到文件中并包含持续时间信息
- 为状态变化发送Slack通知
- 实现心跳机制以确认程序正在运行

## 常用开发命令

### 运行应用程序

直接执行：
```bash
pip install -r requirements.txt
python monitor.py
```

Docker执行（推荐）：
```bash
docker-compose up -d
```

### 配置

`config.yaml` 文件控制以下设置：
- 目标设备（IP或MAC）
- ping间隔和离线阈值
- 日志文件路径
- Slack通知设置
- 心跳间隔（用于程序状态确认）

## 代码模式

1. 使用subprocess执行系统网络命令（ping, arp）
2. 实现带有阈值的状态跟踪以避免误报
3. 提供详细的日志记录，持续时间以中文格式显示
4. 包含网络操作的错误处理
5. 使用YAML进行配置管理