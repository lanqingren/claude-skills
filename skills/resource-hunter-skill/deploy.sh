#!/bin/bash
# 资源猎手 V1.0.0 部署脚本（适配Linux/Mac）
# 规范命名：deploy.sh
# 功能：一键部署、注册技能，检查依赖环境，验证部署结果

# 颜色配置（提升可读性）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # 重置颜色

# 欢迎信息
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}            资源猎手 V1.0.1 部署脚本            ${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "${YELLOW}提示：请确保已安装QClaw（版本≥2.0），且当前目录包含以下4个文件：${NC}"
echo -e "1. resource_hunter.py（核心代码文件）"
echo -e "2. resource_hunter_config.txt（配置说明文件）"
echo -e "3. SKILL.md（上架说明文件）"
echo -e "4. deploy.sh（本部署脚本）"
echo -e ""

# 1. 检查必要文件是否存在
echo -e "${YELLOW}[步骤1/4] 检查部署所需文件...${NC}"
required_files=("resource_hunter.py" "resource_hunter_config.txt" "SKILL.md" "deploy.sh")
missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo -e "${RED}[错误] 缺少以下必要文件，部署失败：${NC}"
    for file in "${missing_files[@]}"; do
        echo -e "  - $file"
    done
    echo -e "${YELLOW}请将所有必要文件放在同一目录下，重新执行脚本。${NC}"
    exit 1
fi
echo -e "${GREEN}[成功] 所有必要文件已找到！${NC}"
echo -e ""

# 2. 检查QClaw依赖环境
echo -e "${YELLOW}[步骤2/4] 检查QClaw依赖环境...${NC}"
if ! command -v qclaw &> /dev/null; then
    echo -e "${RED}[错误] 未检测到QClaw（版本≥2.0），部署失败！${NC}"
    echo -e "${YELLOW}请先安装QClaw，安装命令参考：pip install qclaw>=2.0${NC}"
    exit 1
fi

# 检查QClaw版本
qclaw_version=$(qclaw --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
if [ -z "$qclaw_version" ]; then
    echo -e "${RED}[错误] 无法获取QClaw版本，部署失败！${NC}"
    exit 1
fi

# 版本对比（确保≥2.0）
version_compare=$(echo "$qclaw_version 2.0" | awk '{if ($1 >= $2) print 1; else print 0}')
if [ "$version_compare" -eq 0 ]; then
    echo -e "${RED}[错误] QClaw版本过低（当前版本：$qclaw_version），需≥2.0！${NC}"
    echo -e "${YELLOW}请更新QClaw：pip install --upgrade qclaw${NC}"
    exit 1
fi
echo -e "${GREEN}[成功] QClaw环境正常（版本：$qclaw_version）！${NC}"
echo -e ""

# 3. 部署并注册技能
echo -e "${YELLOW}[步骤3/4] 部署并注册资源猎手V1.0.0技能...${NC}"
# 复制核心文件到QClaw技能目录（适配默认安装路径）
qclaw_skill_dir="$HOME/.qclaw/skills"
if [ ! -d "$qclaw_skill_dir" ]; then
    echo -e "${YELLOW}[提示] QClaw技能目录不存在，自动创建...${NC}"
    mkdir -p "$qclaw_skill_dir"
fi

# 复制核心代码文件到技能目录
cp -f resource_hunter.py "$qclaw_skill_dir/"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 复制核心代码文件失败，部署失败！${NC}"
    exit 1
fi

# 注册技能（调用QClaw注册命令）
qclaw register --skill "$qclaw_skill_dir/resource_hunter.py"
if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 技能注册失败，请检查核心代码文件是否正常！${NC}"
    exit 1
fi
echo -e "${GREEN}[成功] 技能部署并注册完成！${NC}"
echo -e ""

# 4. 验证部署结果
echo -e "${YELLOW}[步骤4/4] 验证部署结果...${NC}"
# 检查技能是否注册成功
registered_skills=$(qclaw list-skills | grep "资源猎手·谜语破译版")
if [ -z "$registered_skills" ]; then
    echo -e "${RED}[错误] 技能注册验证失败，未找到目标技能！${NC}"
    exit 1
fi

echo -e "${GREEN}[成功] 部署验证通过！${NC}"
echo -e ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}          部署完成！使用说明：${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "1. 启动QClaw：qclaw start"
echo -e "2. 触发技能：输入搜索指令（如“找动漫 魔女之旅”）"
echo -e "3. 部署路径：$qclaw_skill_dir"
echo -e "4. 配置修改：编辑 resource_hunter_config.txt 可修改技能参数"
echo -e "5. 注意事项：请先替换核心代码中报错的解析接口（magnet_resolvers、pan_resolvers），避免功能异常"
echo -e ""
echo -e "${YELLOW}提示：若部署后技能无法正常使用，请检查QClaw版本和解析接口配置！${NC}"
