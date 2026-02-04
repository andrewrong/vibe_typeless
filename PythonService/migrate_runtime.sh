#!/bin/bash
# 迁移脚本 - 将旧的模型和日志移动到 runtime 目录

set -e

echo "🔄 Typeless 运行时文件迁移工具"
echo ""

# 检查当前目录
if [ -f "migrate_runtime.sh" ] && [ -f "pyproject.toml" ]; then
    # 已经在 PythonService 目录中
    :
elif [ -d "PythonService" ] && [ -f "PythonService/migrate_runtime.sh" ]; then
    # 在项目根目录，进入 PythonService
    cd PythonService
else
    echo "❌ 错误：无法找到项目目录"
    exit 1
fi

# 创建运行时目录
echo "📁 创建 runtime 目录结构..."
mkdir -p runtime/{logs,models,tmp}

# 检查是否有旧的日志
if [ -d "logs" ] && [ "$(ls -A logs 2>/dev/null)" ]; then
    echo ""
    echo "发现旧的日志文件："
    du -sh logs/* 2>/dev/null || true

    read -p "是否迁移到 runtime/logs? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 迁移日志文件..."
        cp -r logs/* runtime/logs/
        echo "✅ 日志已迁移到 runtime/logs/"
        echo "   可以删除旧目录: rm -rf logs/"
    fi
else
    echo "✅ 没有发现旧日志"
fi

# 检查是否有旧的模型缓存
OLD_HF_CACHE="$HOME/.cache/huggingface/hub"
if [ -d "$OLD_HF_CACHE" ]; then
    # 检查是否有 Whisper 模型
    WHISPER_MODELS=$(find "$OLD_HF_CACHE" -name "*whisper*" -type d 2>/dev/null | wc -l)

    if [ "$WHISPER_MODELS" -gt 0 ]; then
        echo ""
        echo "发现 HuggingFace 模型缓存："
        find "$OLD_HF_CACHE" -name "*whisper*" -type d 2>/dev/null -exec du -sh {} \;

        echo ""
        echo "选项："
        echo "  1. 移动模型（删除旧位置，节省空间）"
        echo "  2. 复制模型（保留旧位置作为备份）"
        echo "  3. 跳过（稍后手动处理）"

        read -p "请选择 (1/2/3): " -n 1 -r
        echo

        case $REPLY in
            1)
                echo "📦 移动模型文件..."
                # 创建目标目录
                mkdir -p runtime/models/hub

                # 移动 Whisper 模型
                find "$OLD_HF_CACHE" -name "*whisper*" -type d -maxdepth 1 -exec mv {} runtime/models/hub/ \;

                echo "✅ 模型已移动到 runtime/models/"
                ;;
            2)
                echo "📦 复制模型文件..."
                mkdir -p runtime/models/hub

                # 复制 Whisper 模型
                find "$OLD_HF_CACHE" -name "*whisper*" -type d -maxdepth 1 -exec cp -r {} runtime/models/hub/ \;

                echo "✅ 模型已复制到 runtime/models/"
                echo "   原始文件仍在: $OLD_HF_CACHE"
                ;;
            3)
                echo "⏭️  跳过模型迁移"
                ;;
            *)
                echo "❌ 无效选择"
                exit 1
                ;;
        esac
    else
        echo "✅ 没有发现 Whisper 模型"
    fi
else
    echo "⚠️  未找到 HuggingFace 缓存目录"
fi

# 设置正确的权限
echo ""
echo "🔐 设置权限..."
chmod -R 755 runtime

# 显示当前状态
echo ""
echo "📊 当前 runtime 目录状态："
du -sh runtime/* 2>/dev/null || true

echo ""
echo "✅ 迁移完成！"
echo ""
echo "下一步："
echo "  1. 测试服务: ./start.sh"
echo "  2. 如果一切正常，可以删除旧文件:"
echo "     rm -rf logs/"
echo "     rm -rf ~/.cache/huggingface/hub/models--*whisper*"
echo ""
