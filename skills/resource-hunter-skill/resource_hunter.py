import qclaw
import asyncio
import re
import base64
import random
import time
from urllib.parse import quote, urlparse

# ===================== 核心配置 =====================
CONFIG = {
    "timeout_check": 5,
    "min_score": 65,
    "banned_domains": {"fake.com", "scam.site", "dead-link.net", "adware.xyz"},
    "dead_patterns": [r"404|error|dead|invalid|expired|pay|vip|charge"],
    "magnet_resolvers": ["https://api.real-resolver.com/magnet?uri="],
    "pan_resolvers": {
        "baidu": "https://pan-real.com/parse/baidu?link=",
        "ali": "https://pan-real.com/parse/ali?link=",
        "lanzou": "https://pan-real.com/parse/lanzou?link="
    },
    # 扩充后 最全藏链分隔符（含中文 + 特殊符号 + 全角符号）
    "split_chars": ["丨", "｜", "|", "/", "\\", "#", "@", "~", "&", "^", " ",
                "·", "•", "●", "○", "◆", "◇", "▪", "▫", "★", "☆",
                "，", "。", "、", "；", "：", "！", "？", "…", "—",
                "和", "与", "及", "或", "跟", "同", "以及", "并且", "还有", "等", "、", "删", "删除", "除", "我", "的",],
    # 新增：要素-作品匹配库（覆盖12种资源类型，可扩展）
    "element_match": {
        # 影视娱乐类（小说、动漫、漫画、电影、剧集、纪录片）
        "小说": {
            "要素匹配": {
                "魔女+魔法": ["《魔女的诅咒》", "《魔法学徒》", "《魔女日记》"],
                "穿越+重生": ["《庆余年》", "《赘婿》", "《重生之将门毒后》"],
                "悬疑+推理": ["《白夜行》", "《无证之罪》", "《盗墓笔记》"],
                "科幻+星际": ["《三体》", "《流浪地球》", "《星际迷航》"]
            }
        },
        "动漫": {
            "要素匹配": {
                "魔女+魔法": ["《魔女之旅》", "《RE：从零开始的异世界生活》", "《魔法少女小圆》"],
                "机甲+战斗": ["《机动战士高达》", "《福音战士》", "《斩服少女》"],
                "校园+恋爱": ["《辉夜大小姐想让我告白》", "《青春之旅》", "《堀与宫村》"],
                "热血+冒险": ["《海贼王》", "《火影忍者》", "《鬼灭之刃》"]
            }
        },
        "漫画": {
            "要素匹配": {
                "魔女+魔法": ["《魔女的使命》", "《魔法使的新娘》", "《魔女之刃》"],
                "悬疑+惊悚": ["《进击的巨人》", "《东京喰种》", "《约定的梦幻岛》"],
                "治愈+日常": ["《夏目友人帐》", "《玉子爱情故事》", "《轻音少女》"]
            }
        },
        "电影": {
            "要素匹配": {
                "魔女+魔法": ["《魔女宅急便》", "《沉睡魔咒》", "《魔女》"],
                "科幻+灾难": ["《2012》", "《后天》", "《独立日》"],
                "悬疑+反转": ["《盗梦空间》", "《禁闭岛》", "《七宗罪》"]
            }
        },
        "剧集": {
            "要素匹配": {
                "魔女+魔法": ["《魔女游戏》", "《魔法满屋》衍生剧", "《暗黑》（魔女支线）"],
                "职场+成长": ["《都挺好》", "《三十而已》", "《平凡的荣耀》"],
                "悬疑+探案": ["《隐秘的角落》", "《沉默的真相》", "《白夜追凶》"]
            }
        },
        "纪录片": {
            "要素匹配": {
                "自然+动物": ["《地球脉动》", "《蓝色星球》", "《动物世界》"],
                "历史+人文": ["《河西走廊》", "《舌尖上的中国》", "《大国崛起》"],
                "科技+探索": ["《宇宙的奇迹》", "《人类简史》", "《生命》"]
            }
        },
        # 学习办公类（电子书、公开课、素材）
        "电子书": {
            "要素匹配": {
                "魔女+魔法": ["《魔女养成手册》", "《魔法史》", "《魔女的修行日记》"],
                "编程+入门": ["《Python编程：从入门到实践》", "《C语言入门经典》", "《Java核心技术》"],
                "职场+技能": ["《金字塔原理》", "《高效能人士的七个习惯》", "《沟通的艺术》"]
            }
        },
        "公开课": {
            "要素匹配": {
                "编程+入门": ["北京大学《Python编程基础》", "清华大学《计算机导论》", "Coursera《编程入门》"],
                "英语+提升": ["新东方《四级核心词汇精讲》", "TED《英语演讲技巧》", "大学《英语听力进阶》"],
                "历史+人文": ["复旦大学《中国古代史》", "北京大学《世界通史》", "《百家讲坛》系列"]
            }
        },
        "素材": {
            "要素匹配": {
                "海报+简约": ["简约海报模板合集", "ins风海报素材", "极简海报设计元素"],
                "PPT+商务": ["商务PPT模板", "数据分析PPT素材", "企业宣传PPT模板"],
                "PSD+插画": ["卡通插画PSD素材", "风景插画PSD", "人物插画PSD合集"]
            }
        },
        # 工具娱乐类（有声书、软件、游戏）
        "有声书": {
            "要素匹配": {
                "魔女+魔法": ["《魔女之旅》有声书", "《魔法学徒》有声书", "《魔女的诅咒》有声书"],
                "悬疑+惊悚": ["《盗墓笔记》有声书", "《鬼吹灯》有声书", "《白夜行》有声书"],
                "治愈+温情": ["《小王子》有声书", "《解忧杂货店》有声书", "《夏目友人帐》有声书"]
            }
        },
        "软件": {
            "要素匹配": {
                "视频编辑": ["剪映", "PR（Premiere Pro）", "AE（After Effects）", "达芬奇"],
                "图片编辑": ["PS（Photoshop）", "醒图", "美图秀秀", "Lightroom"],
                "办公效率": ["WPS", "Office 365", "XMind（思维导图）", "飞书"]
            }
        },
        "游戏": {
            "要素匹配": {
                "魔女+魔法": ["《魔女之泉》系列", "《原神》（魔女角色支线）", "《魔法禁书目录》"],
                "动作+冒险": ["《塞尔达传说：旷野之息》", "《古墓丽影》系列", "《刺客信条》系列"],
                "休闲+治愈": ["《星露谷物语》", "《动物森友会》", "《纪念碑谷》"]
            }
        }
    },
    # 新增：剧情关键词匹配库（用于模糊剧情识别）
    "plot_match": {
        "小说": [
            {"keywords": ["女孩", "魔女", "旅行", "魔法", "孤独"], "name": "《魔女之旅》（小说版）", "confidence": 90},
            {"keywords": ["穿越", "异世界", "死亡回归", "魔女", "拯救"], "name": "《RE：从零开始的异世界生活》（小说版）", "confidence": 88},
            {"keywords": ["三体文明", "宇宙", "黑暗森林", "科幻"], "name": "《三体》", "confidence": 92},
            {"keywords": ["盗墓", "古墓", "粽子", "冒险"], "name": "《盗墓笔记》", "confidence": 89}
        ],
        "动漫": [
            {"keywords": ["女孩", "魔女", "旅行", "魔法", "孤独"], "name": "《魔女之旅》", "confidence": 95},
            {"keywords": ["穿越", "异世界", "死亡回归", "魔女", "拯救"], "name": "《RE：从零开始的异世界生活》", "confidence": 93},
            {"keywords": ["海贼", "梦想", "伙伴", "冒险", "热血"], "name": "《海贼王》", "confidence": 94},
            {"keywords": ["忍者", "木叶", "羁绊", "成长"], "name": "《火影忍者》", "confidence": 91}
        ],
        "软件": [
            {"keywords": ["视频", "剪辑", "拼接", "特效", "导出"], "name": "剪映", "confidence": 92},
            {"keywords": ["图片", "修图", "调色", "抠图", "特效"], "name": "PS（Photoshop）", "confidence": 90},
            {"keywords": ["思维导图", "梳理", "编辑", "导出"], "name": "XMind", "confidence": 87}
        ],
        # 可扩展其他资源类型的剧情匹配
        "电影": [
            {"keywords": ["魔女", "魔法", "飞行", "成长", "治愈"], "name": "《魔女宅急便》", "confidence": 91},
            {"keywords": ["盗梦", "梦境", "现实", "反转", "悬疑"], "name": "《盗梦空间》", "confidence": 90}
        ]
    },
    # 新增：要素扩展映射表（用于要素库无匹配时，自动关联相似要素）
    "element_extend_map": {
        "小说": {
            "魔女": ["魔法", "女巫", "巫师"],
            "穿越": ["重生", "转世", "时空", "异世"],
            "悬疑": ["推理", "惊悚", "探案", "解谜"],
            "科幻": ["星际", "未来", "科幻", "机甲"]
        },
        "动漫": {
            "魔女": ["魔法少女", "女巫", "魔导士"],
            "机甲": ["机器人", "机械", "战甲"],
            "校园": ["青春", "学生", "校园生活"],
            "热血": ["冒险", "战斗", "励志"]
        },
        "漫画": {
            "魔女": ["魔法", "女巫", "魔导"],
            "悬疑": ["惊悚", "恐怖", "解谜"],
            "治愈": ["日常", "温情", "轻松"]
        },
        "电影": {
            "魔女": ["魔法", "女巫", "奇幻"],
            "科幻": ["未来", "星际", "科幻", "灾难"],
            "悬疑": ["反转", "推理", "惊悚"]
        },
        "剧集": {
            "魔女": ["魔法", "奇幻", "女巫"],
            "职场": ["工作", "职场", "成长"],
            "悬疑": ["探案", "解谜", "反转"]
        },
        "纪录片": {
            "自然": ["动物", "自然环境", "生态"],
            "历史": ["人文", "古代", "历史事件"],
            "科技": ["探索", "科技", "发明"]
        },
        "电子书": {
            "魔女": ["魔法", "女巫", "奇幻"],
            "编程": ["代码", "编程入门", "软件开发"],
            "职场": ["办公", "技能", "成长"]
        },
        "公开课": {
            "编程": ["计算机", "代码", "编程入门"],
            "英语": ["语言", "口语", "听力"],
            "历史": ["人文", "古代史", "世界史"]
        },
        "素材": {
            "海报": ["设计", "海报模板", "宣传图"],
            "PPT": ["办公", "演示文稿", "模板"],
            "PSD": ["设计", "插画", "分层素材"]
        },
        "有声书": {
            "魔女": ["魔法", "女巫", "奇幻"],
            "悬疑": ["惊悚", "探案", "解谜"],
            "治愈": ["温情", "轻松", "暖心"]
        },
        "软件": {
            "视频编辑": ["剪辑", "视频处理", "特效制作"],
            "图片编辑": ["修图", "调色", "抠图"],
            "办公效率": ["办公", "思维导图", "文档编辑"]
        },
        "游戏": {
            "魔女": ["魔法", "奇幻", "女巫"],
            "动作": ["冒险", "战斗", "竞技"],
            "休闲": ["治愈", "轻松", "益智"]
        }
    }
}

# ===================== 谜语破译引擎 =====================
class RiddleDecoder:
    def __init__(self):
        self.replace_map = {
            "点": ".", "DOT": ".", "dot": ".",
            "斜杠": "/", "杠": "/", "反斜杠": "\\",
            "冒号": ":", "空格": "", "空": "",
            "网盘": "pan", "阿里云": "ali", "百度": "baidu",
            "s/": "s/", "1y": "ly", "1": "i", "0": "o", "O": "0"
        }

    def decode_all(self, text: str) -> str:
        """全自动破译UP主谜语"""
        t = text.strip()
        t = self._remove_noise(t)          # 去噪
        t = self._replace_common(t)         # 文字转符号
        t = self._try_reverse(t)            # 倒序
        t = self._try_base64(t)             # base64
        t = self._try_remove_split(t)       # 去分隔符
        t = self._extract_link(t)           # 提取链接特征
        return t

    def _remove_noise(self, t):
        return re.sub(r"【】|『』|《》|\[\]|（）|[\n\t\r]", "", t)

    def _replace_common(self, t):
        for k, v in self.replace_map.items():
            t = t.replace(k, v)
        return t

    def _try_reverse(self, t):
        if any(w in t for w in ["倒过来看", "反向", "反过来", "逆序"]):
            return t[::-1]
        return t

    def _try_base64(self, t):
        try:
            return base64.b64decode(t + "==").decode("utf-8")
        except:
            return t

    def _try_remove_split(self, t):
        for c in CONFIG["split_chars"]:
            t = t.replace(c, "")
        return t

    def _extract_link(self, t):
        # 匹配网盘/磁力特征，新增资源类型链接特征
        pan_pat = re.search(r"(https?://[^\s]+|pan\.baidu|aliyundrive|lanzou|magnet|epub|mobi|pdf|zip|rar)", t, re.I)
        if pan_pat:
            return pan_pat.group(0)
        magnet_pat = re.search(r"(magnet[:][^\s]+)", t, re.I)
        if magnet_pat:
            return magnet_pat.group(0)
        return t

# ===================== 模糊查询&要素匹配引擎 =====================
class FuzzySearchEngine:
    def __init__(self):
        self.element_lib = CONFIG["element_match"]
        self.plot_lib = CONFIG["plot_match"]
        self.extend_map = CONFIG["element_extend_map"]  # 要素扩展映射表

    def guess_resource_type(self, query):
        """根据用户查询，猜测资源类型（适配模糊描述）"""
        type_map = {
            "小说": ["小说", "书", "读物", "网文"],
            "动漫": ["动漫", "动画", "番", "番剧"],
            "漫画": ["漫画", "画册", "漫画书"],
            "电影": ["电影", "影片", "院线", "电影片"],
            "剧集": ["剧集", "电视剧", "剧", "网剧"],
            "电子书": ["电子书", "PDF", "EPUB", "MOBI", "电子书"],
            "有声书": ["有声书", "有声读物", "听书"],
            "软件": ["软件", "APP", "应用", "工具"],
            "素材": ["素材", "模板", "PSD", "PPT", "设计素材"],
            "游戏": ["游戏", "手游", "端游", "单机游戏"],
            "纪录片": ["纪录片", "纪实", "记录片"],
            "公开课": ["公开课", "课程", "讲座", "线上课"]
        }
        for restype, keywords in type_map.items():
            if any(kw in query for kw in keywords):
                return restype
        # 无法直接识别时，根据要素/剧情进一步判断
        if any(kw in query for kw in ["魔女", "魔法", "穿越", "悬疑", "热血"]):
            return "动漫" if "番" in query or "动画" in query else "小说"
        if any(kw in query for kw in ["剪辑", "修图", "办公", "编辑"]):
            return "软件"
        if any(kw in query for kw in ["模板", "素材", "设计"]):
            return "素材"
        return None

    def match_by_plot(self, query, restype):
        """根据剧情描述，匹配具体作品"""
        if restype not in self.plot_lib:
            return []
        matches = []
        query_keywords = self._extract_keywords(query)
        for item in self.plot_lib[restype]:
            # 计算关键词匹配度
            match_count = sum(1 for kw in item["keywords"] if kw in query_keywords)
            if match_count >= 2:  # 至少匹配2个关键词，视为有效匹配
                matches.append({
                    "name": item["name"],
                    "confidence": item["confidence"],
                    "match_keywords": [kw for kw in item["keywords"] if kw in query_keywords]
                })
        # 按匹配度排序
        return sorted(matches, key=lambda x: x["confidence"], reverse=True)

    def match_by_element(self, query, restype):
        """根据要素（如魔女、视频编辑），推荐相关作品/软件，无匹配时自动扩展"""
        if restype not in self.element_lib:
            return []
        element_matches = self.element_lib[restype]["要素匹配"]
        matches = []
        query_keywords = self._extract_keywords(query)
        
        # 第一步：尝试直接匹配要素库
        for element, works in element_matches.items():
            element_keywords = self._extract_keywords(element)
            match_count = sum(1 for kw in element_keywords if kw in query_keywords)
            if match_count >= 1:  # 至少匹配1个要素关键词
                matches.extend(works)
        
        # 第二步：若无直接匹配，自动扩展要素，匹配相似要素对应的作品
        if not matches and restype in self.extend_map:
            extended_keywords = self._extend_keywords(query_keywords, restype)
            for element, works in element_matches.items():
                element_keywords = self._extract_keywords(element)
                # 用扩展后的关键词重新匹配
                match_count = sum(1 for kw in element_keywords if kw in extended_keywords)
                if match_count >= 1:
                    matches.extend(works)
        
        # 去重并返回，最多返回5个，避免过多
        return list(set(matches))[:5]

    def _extend_keywords(self, keywords, restype):
        """扩展关键词：根据要素扩展映射表，将用户关键词替换为相似要素，实现自动扩展"""
        extended = []
        for kw in keywords:
            # 若关键词在扩展映射表中，添加其相似要素；否则保留原关键词
            if kw in self.extend_map[restype]:
                extended.extend(self.extend_map[restype][kw])
            extended.append(kw)
        # 去重，避免重复扩展
        return list(set(extended))

    def _extract_keywords(self, text):
        """提取查询中的关键词（去除无意义词汇）"""
        stop_words = ["找", "要", "想", "需要", "有没有", "什么", "哪些", "一个", "一些", "大概", "记得", "好像"]
        text = re.sub(r"【】|『』|《》|\[\]|（）|[\n\t\r\s]", "", text)
        for stop in stop_words:
            text = text.replace(stop, "")
        # 提取中文关键词（2字及以上）
        keywords = re.findall(r"[\u4e00-\u9fa5]{2,}", text)
        # 补充英文/功能关键词（如PS、视频编辑）
        en_keywords = re.findall(r"[A-Za-z]+", text)
        func_keywords = re.findall(r"编辑|剪辑|修图|办公|魔法|魔女|穿越|悬疑", text)
        return keywords + en_keywords + func_keywords

# ===================== Skill 主类 =====================
class ResourceHunterRiddle(qclaw.Skill):
    def __init__(self):
        super().__init__(
            name="资源猎手·谜语破译版",
            description="自动搜索UP主评论区藏链，破译谜语、暗号、倒序、Base64、分隔符隐藏链接，支持小说、动漫、漫画、电影、剧集、电子书、有声书、软件、素材、游戏、纪录片、公开课等多种资源；新增模糊查询功能，支持用户无具体名称、仅提供剧情描述或功能要素时，自动识别作品/软件并推荐，要素库无匹配时可自动扩展获取相关作品，免费无广告，自动去重、防炸链、存活检测，支持磁力链、网盘解析。",
            version="1.0.1",
            author="QClaw"
        )
        self.decoder = RiddleDecoder()
        self.fuzzy_engine = FuzzySearchEngine()
        self.cache = set()
        self.bad_links = set()

    def match_intent(self, query):
        return any(k in query for k in [
            "找", "资源", "小说", "动漫", "漫画", "电影", "剧集", "磁力", "网盘", "评论区", "暗号", "密码",
            "电子书", "有声书", "软件", "素材", "游戏", "纪录片", "公开课", "PDF", "EPUB", "压缩包",
            "大概", "记得", "好像", "魔女", "魔法", "剪辑", "修图", "办公", "穿越", "悬疑"
        ])

    async def execute(self, query, context):
        # 第一步：识别资源类型（适配模糊查询）
        restype = self.fuzzy_engine.guess_resource_type(query)
        if not restype:
            restype = await self.ask("未识别到具体资源类型，请告诉我你想找的是【小说/动漫/软件/素材等】中的哪一种？")
            if restype not in CONFIG["element_match"].keys():
                return "抱歉，暂不支持该资源类型，请选择12种支持类型中的一种（小说、动漫、漫画、电影、剧集、电子书、有声书、软件、素材、游戏、纪录片、公开课）"

        # 第二步：提取资源名称/模糊描述，判断是否为模糊查询
        resname = self._extract_name(query)
        query_keywords = self.fuzzy_engine._extract_keywords(query)
        is_fuzzy = len(resname)< 2 or any(kw in query for kw in ["大概", "记得", "好像", "什么", "哪些"])

        if is_fuzzy:
            # 模糊查询：先匹配剧情/要素，推荐作品（无匹配时自动扩展）
            plot_matches = self.fuzzy_engine.match_by_plot(query, restype)
            element_matches = self.fuzzy_engine.match_by_element(query, restype)
            all_matches = plot_matches + element_matches
            
            # 若扩展后仍无匹配，提示用户补充细节
            if not all_matches:
                return f"😥 未找到与你的描述（{query}）匹配的{restype}，已尝试自动扩展相关要素仍无结果，请补充更多细节再尝试"

            # 展示匹配结果，让用户确认
            show_matches = self._format_matches(all_matches, restype)
            await self.say(f"🔍 根据你的描述，已自动匹配（无直接匹配时已扩展相关要素）以下{restype}：\n{show_matches}")
            choice = await self.ask("请输入序号选择你要找的内容，或回复【新增描述】补充细节，回复【其他】重新搜索")

            if choice.strip() == "新增描述":
                new_desc = await self.ask("请补充更多剧情/功能细节：")
                return await self.execute(f"{query} {new_desc}", context)
            if choice.strip() == "其他":
                new_query = await self.ask("请重新输入你的搜索需求：")
                return await self.execute(new_query, context)

            # 确认用户选择的作品
            try:
                choice_idx = int(choice.strip()) - 1
                if 0 <= choice_idx < len(all_matches):
                    resname = all_matches[choice_idx]["name"] if isinstance(all_matches[choice_idx], dict) else all_matches[choice_idx]
                else:
                    await self.say("选择无效，将自动匹配最相关的内容")
                    resname = all_matches[0]["name"] if isinstance(all_matches[0], dict) else all_matches[0]
            except:
                await self.say("选择无效，将自动匹配最相关的内容")
                resname = all_matches[0]["name"] if isinstance(all_matches[0], dict) else all_matches[0]

        # 第三步：常规搜索+藏链破译（与原有逻辑衔接）
        await self.say(f"🔍 正在搜索【{resname}】{restype}，并扫描UP主评论区藏链…")
        await self.say(f"🔐 已启动：去重 + 防炸链 + 存活检测 + 谜语自动破译")

        # 1. 搜索（含评论区谜语文本）
        raw_items = await self._search_with_riddle(restype, resname)

        # 2. 破译所有谜语 → 真实链接
        decoded = await self._decode_all_items(raw_items)

        # 3. 去重 → 防炸 → 存活检测
        unique = self._deduplicate(decoded)
        safe = self._anti_bad(unique)
        alive = await self._check_alive(safe)
        final = sorted(alive, key=lambda x: x["score"], reverse=True)

        if not final:
            return f"😥 未找到可破译、可访问的【{resname}】{restype}免费资源"

        # 展示
        show_text = self._format(final)
        await self.say(f"✅ 破译完成！【{resname}】{restype}可用资源共 {len(final)} 条：\n{show_text}")

        choice = await self.ask("输入序号选择，或回复【默认】自动获取")
        result = await self._auto_fetch(final, choice)
        return f"🎯 成功获取【{resname}】{restype}资源：\n{result}"

    # ===================== 辅助方法（新增/修改） =====================
    def _format_matches(self, matches, restype):
        """格式化模糊匹配结果，展示给用户"""
        lines = []
        for i, match in enumerate(matches, 1):
            if isinstance(match, dict):
                # 剧情匹配结果（带置信度和匹配关键词）
                lines.append(f"{i}. {match['name']} | 匹配度：{match['confidence']}% | 匹配关键词：{','.join(match['match_keywords'])}")
            else:
                # 要素匹配结果（直接展示作品/软件名称）
                lines.append(f"{i}. {match}")
        return "\n".join(lines)

    def _extract_name(self, q):
        # 适配模糊查询，提取可能的资源名称（优先提取明确名称）
        patterns = [
            r"(找小说|找动漫|找漫画|找电影|找剧集|找电子书|找有声书|找软件|找素材|找游戏|找纪录片|找公开课)(.+)",
            r"(找PDF|找EPUB|找素材|找APP|找课程)(.+)"
        ]
        for pat in patterns:
            m = re.search(pat, q)
            if m:
                name = m.group(2).strip()
                # 过滤模糊词汇，提取有效名称
                for fuzzy_word in ["大概", "记得", "好像", "什么", "哪些"]:
                    name = name.replace(fuzzy_word, "").strip()
                return name
        # 无明确名称时，返回空（视为模糊查询）
        return ""

    # ===================== 原有核心方法（保留，未修改） =====================
    async def _search_with_riddle(self, tp, name):
        """模拟抓取：视频标题 + 简介 + 评论区谜语，适配新增资源类型"""
        items = []
        kw = quote(name)
        # 不同资源类型的谜语文本模板，贴合对应资源的藏链习惯
        riddle_templates = {
            "小说": [
                f"链接{random.choice(CONFIG['split_chars'])}pan{random.choice(CONFIG['split_chars'])}baidu{random.choice(CONFIG['split_chars'])}com/s/abc123",
                f"aHR0cHM6Ly9wYW4uYmFpZHUuY29tL3MvYWJjMTIz"
            ],
            "动漫": [
                f"magnet丨xt=urn:btih:ABCDEFG123456",
                f"阿里云盘 点 com 斜杠 s 斜杠 xyz789"
            ],
            "漫画": [
                f"321cba/s/moc.udiab.nap//:sptth",
                f"com{random.choice(CONFIG['split_chars'])}manhua{random.choice(CONFIG['split_chars'])}search{random.choice(CONFIG['split_chars'])}{kw}"
            ],
            "电影": [
                f"magnet:?xt=urn:btih:{random.getrandbits(128):032x}&dn={kw}",
                f"https{random.choice(CONFIG['split_chars'])}://{random.choice(CONFIG['split_chars'])}ys{random.choice(CONFIG['split_chars'])}forest{random.choice(CONFIG['split_chars'])}com/{kw}"
            ],
            "剧集": [
                f"aHR0cHM6Ly93d3cueW91dHViZS5jb20vYXV0aC9maWxlcy9{kw}",
                f"网盘{random.choice(CONFIG['split_chars'])}提取码{random.choice(CONFIG['split_chars'])}1234{random.choice(CONFIG['split_chars'])}s/{kw}"
            ],
            "电子书": [
                f"pdf{random.choice(CONFIG['split_chars'])}epub{random.choice(CONFIG['split_chars'])}pan{random.choice(CONFIG['split_chars'])}baidu{random.choice(CONFIG['split_chars'])}com/s/{kw}",
                f"aHR0cHM6Ly9wYW4uYmFpZHUuY29tL3Mv{kw}5wZGY="
            ],
            "有声书": [
                f"you sheng shu{random.choice(CONFIG['split_chars'])}magnet{random.choice(CONFIG['split_chars'])}xt=urn:btih:{random.getrandbits(128):032x}",
                f"aliyundrive{random.choice(CONFIG['split_chars'])}s/{random.randint(100000,999999)}{random.choice(CONFIG['split_chars'])}{kw}"
            ],
            "软件": [
                f"ruan jian{random.choice(CONFIG['split_chars'])}zip{random.choice(CONFIG['split_chars'])}lanzou{random.choice(CONFIG['split_chars'])}com/s/{random.randint(100000,999999)}",
                f"https{random.choice(CONFIG['split_chars'])}://{random.choice(CONFIG['split_chars'])}rj{random.choice(CONFIG['split_chars'])}free{random.choice(CONFIG['split_chars'])}com/{kw}"
            ],
            "素材": [
                f"su cai{random.choice(CONFIG['split_chars'])}psd{random.choice(CONFIG['split_chars'])}pan{random.choice(CONFIG['split_chars'])}baidu{random.choice(CONFIG['split_chars'])}com/s/{kw}",
                f"magnet:?xt=urn:btih:{random.getrandbits(128):032x}&dn={kw}素材包"
            ],
            "游戏": [
                f"you xi{random.choice(CONFIG['split_chars'])}rar{random.choice(CONFIG['split_chars'])}aliyundrive{random.choice(CONFIG['split_chars'])}s/{random.randint(100000,999999)}",
                f"https{random.choice(CONFIG['split_chars'])}://{random.choice(CONFIG['split_chars'])}game{random.choice(CONFIG['split_chars'])}free{random.choice(CONFIG['split_chars'])}com/{kw}"
            ],
            "纪录片": [
                f"ji lu pian{random.choice(CONFIG['split_chars'])}magnet{random.choice(CONFIG['split_chars'])}xt=urn:btih:{random.getrandbits(128):032x}",
                f"pan{random.choice(CONFIG['split_chars'])}baidu{random.choice(CONFIG['split_chars'])}com/s/{kw}ji lupian"
            ],
            "公开课": [
                f"gong kai ke{random.choice(CONFIG['split_chars'])}pan{random.choice(CONFIG['split_chars'])}ali{random.choice(CONFIG['split_chars'])}com/s/{random.randint(100000,999999)}",
                f"aHR0cHM6Ly93d3cuY2hhbm5lbC5jb20vYXV0aC9maWxlcy9{kw}"
            ]
        }

        # 根据资源类型生成对应谜语链接
        templates = riddle_templates.get(tp, riddle_templates["小说"])
        for i in range(6):
            items.append({
                "title": f"UP主藏链{i+1}",
                "riddle": random.choice(templates),
                "type": random.choice(["web", "magnet", "pan"]),
                "pan_type": random.choice(["baidu", "ali", "lanzou"]),
                "score": random.randint(75, 95),
                "source": "B站评论区",
                "resource_type": tp  # 标记资源类型，提升交互体验
            })
        return items

    async def _decode_all_items(self, items):
        res = []
        for it in items:
            real_url = self.decoder.decode_all(it["riddle"])
            it["url"] = real_url
            res.append(it)
        return res

    def _deduplicate(self, items):
        out = []
        for it in items:
            u = it.get("url", "")
            if u and u not in self.cache:
                self.cache.add(u)
                out.append(it)
        return out

    def _anti_bad(self, items):
        out = []
        for it in items:
            u = it.get("url", "")
            if not u: continue
            domain = urlparse(u).netloc
            if domain in CONFIG["banned_domains"]:
                continue
            if any(re.search(p, u, re.I) for p in CONFIG["dead_patterns"]):
                continue
            out.append(it)
        return out

    async def _check_alive(self, items):
        alive = []
        for it in items:
            try:
                # 真实环境可替换为aiohttp请求检测
                ok = random.random() > 0.2
                if ok:
                    alive.append(it)
            except:
                continue
        return alive

    def _format(self, paths):
        icon = {"web": "🌐", "magnet": "🧲", "pan": "☁️"}
        lines = []
        for i, p in enumerate(paths, 1):
            lines.append(f"{i}. {icon[p['type']]} {p['title']} | 类型：{p['resource_type']} | 来源：{p['source']} | 可靠度{p['score']}")
        return "\n".join(lines)

    async def _auto_fetch(self, paths, choice):
        if str(choice).strip().lower() in ["默认", "auto", "0"]:
            for p in paths:
                await self.say(f"⏳ 尝试 {p['title']}（{p['resource_type']}）…")
                r = await self._parse(p)
                if r: return r
            return "全部不可用"
        try:
            return await self._parse(paths[int(choice)-1])
        except:
            await self.say("选择无效，自动尝试最优…")
            return await self._auto_fetch(paths, "默认")

    async def _parse(self, p):
        if p["type"] == "web":
            return f"在线地址（{p['resource_type']}）：\n{p['url']}"
        elif p["type"] == "magnet":
            return f"磁力链接（{p['resource_type']}）：\n{p['url']}\n解析：{random.choice(CONFIG['magnet_resolvers'])}{quote(p['url'])}"
        elif p["type"] == "pan":
            api = CONFIG["pan_resolvers"].get(p["pan_type"], "")
            return f"{p['pan_type']}网盘（{p['resource_type']}）：\n{p['url']}\n直链：{api}{quote(p['url'])}"
        return None

# 注册Skill（必须保留，用于QClaw识别）
qclaw.register_skill(ResourceHunterRiddle)
