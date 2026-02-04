#!/bin/bash
# 清理旧的模型缓存目录

echo "🧹 清理旧的模型缓存"
echo ""

# 检查目录
if [ -f "cleanup_old_cache.sh" ] && [ -f "pyproject.toml" ]; then
    # 已经在 PythonService 目录中
    :
elif [ -d "PythonService" ] && [ -f "PythonService/cleanup_old_cache.sh" ]; then
    # 在项目根目录，进入 PythonService
    cd PythonService
else
    echo "❌ 错误：无法找到项目目录"
    exit 1
fi

# 检查旧缓存
OLD_CACHE="$HOME/.cache/typeless"

if [ ! -d "$OLD_CACHE" ]; then
    echo "✅ 没有找到旧缓存目录: $OLD_CACHE"
    echo "   不需要清理"
    exit 0
fi

# 显示旧缓存大小
SIZE=$(du -sh "$OLD_CACHE" 2>/dev/null | cut -f1)
echo "📁 发现旧缓存目录:"
echo "   位置: $OLD_CACHE"
echo "   大小: $SIZE"
echo ""

# 列出内容
echo "📋 内容:"
ls -lh "$OLD_CACHE" 2>/dev/null || echo "   (无法读取)"
echo ""

read -p "是否删除旧缓存? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  删除旧缓存..."
    rm -rf "$OLD_CACHE"

    if [ ! -d "$OLD_CACHE" ]; then
        echo "✅ 旧缓存已删除"
    else
        echo "❌ 删除失败，请手动删除: rm -rf $OLD_CACHE"
    fi
else
    echo "⏭️  跳过删除"
fi

echo ""
echo "📊 当前模型位置:"
echo "   Whisper: $(pwd)/runtime/models/"
echo "   VAD: $(pwd)/runtime/models/vad/"
echo ""
echo "✅ 完成！"
