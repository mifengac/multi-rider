# -*- coding: utf-8 -*-
"""
申报书自动填充脚本(精简版,每节控制在1-2页,整份不超过15页)。

输出:
  shenbaoshu-filled.doc            -- 方法论版(三大方法论口径)
  shenbaoshu-filled-xingzhen.doc   -- 刑侦合成作战版(刑侦话术口径)

公文格式:
  一级标题 一、二、三       -> 黑体 三号
  二级标题 (一)(二)(三)     -> 楷体_GB2312 三号
  三级标题 1./1、/(1)/(1)   -> 仿宋_GB2312 三号 加粗
  正文                       -> 仿宋_GB2312 三号 + 首行缩进2字符
  行距 28 磅(固定值)
"""

import os
import re
import sys
import time
import pythoncom
import win32com.client


def _retry_com(fn, retries=8, delay=0.5):
    """重试包装,规避 Word COM 偶发 'Call was rejected by callee' (RPC_E_CALL_REJECTED) 等。"""
    last_exc = None
    for _ in range(retries):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise last_exc

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "shenbaoshu-o.doc")
OUT_M = os.path.join(ROOT, "shenbaoshu-filled.doc")            # 方法论版(原版)
OUT_X = os.path.join(ROOT, "shenbaoshu-filled-xingzhen.doc")   # 刑侦合成作战版

# ---- 公文格式常量 ----
SAN_HAO_PT = 16                # 三号字号 = 16pt
LINE_SPACING_PT = 28           # 28磅行距(固定值)
FIRST_LINE_INDENT_PT = 32      # 2字符 ≈ 32pt(三号)
WD_LINE_SPACE_EXACTLY = 4
WD_ALIGN_LEFT = 0

H1_RE = re.compile(r"^[一二三四五六七八九十百]+、")
H2_RE = re.compile(r"^[\u0028\uff08][一二三四五六七八九十]+[\u0029\uff09]")
H3_RE = re.compile(
    r"^(?:\d+[、.\uff0e]|[\u0028\uff08]\d+[\u0029\uff09])"
)


# ----------------------------- 公共基本信息 -----------------------------

PROJECT_NAME = "「刑智·护苗」涉未成年人违法犯罪预防数字侦查智慧平台"
APPLICANT_UNIT = "XX市公安局治安管理支队(具体到业务大队)"
MAIN_CREATOR = "(待补充:姓名/职务/警号)"
PARTICIPANTS = "(待补充:协作单位民警名单)"

APPLICATION_SCENARIO = (
    "☐智能办公  ☑决策辅助  ☑研判分析  ☑自动化流程\r"
    "☐学习问答  ☑特征提取  ☐开源情报  ☑其他(刑侦数字侦查/视频证据取证/未成年人犯罪预防)"
)
PRODUCT_FORM = (
    "☐功能模块  ☑应用程序  ☐小程序   ☐APP   ☑网页\r"
    "☑智能体    ☐脚本      ☐插件     ☐其他"
)


# ============================ 方法论版(原稿) ============================

SUMMARY = (
    "针对基层公安在涉未成年人违法犯罪预防中长期存在的「侦查警力被低价值人工感知劳动"
    "消耗、'图—情—指'三系统切换之痛、数字侦查'算得出、落不下'(预警与跨部门分级干预"
    "最后一公里断裂)」三大共性痛点,本作品立足\"AI+\"侦查能力,聚焦预防打击未成年人"
    "违法犯罪。以全省首例民警零基础自训YOLO26\"飙车炸街翘车头\"细分违法识别模型为"
    "独具一帜的切入点,叠加InsightFace人像、Neo4j异构图谱、GraphSAGE团伙圈层研判、"
    "微软GraphRAG笔录串并、Gemma3-4B本地文书辅助,形成\"AI替代人工感知阵地化、基层"
    "版图情指一体化、工单化闭环+合成机制常态化\"三大可复制方法论。前身在飙车炸街"
    "专项整治中累计研判卡口图片逾100万张、释放专职筛图警力2名、警情同比降11.8%、"
    "攻坚阶段降幅37.4%、处置涉案未成年人20余名零再犯,实战检验通过。全栈开源、零"
    "采购、内网部署、数据不出公安网。"
)

SECTION_1 = (
    "一、运行环境\r"
    "i5+16GB+4GB显存普通工作站即承载;Python3.12+Flask+Neo4j+Docker+Ollama;模型栈含"
    "YOLO26+YOLOE-26+InsightFace+GraphSAGE+微软GraphRAG+Gemma3-4B-Int4;数据底座贯通"
    "公安/教育/民政/卫健/残联/法院/检察/信访8+部门2.4亿+条。\r"
    "\r"
    "二、操作流程(以飙车炸街涉未成年人专案为例)\r"
    "1. 民警下班前框选时段+卡口,夜间YOLO26自动批量推理(单机500张/分钟)沉淀证据包;\r"
    "2. 次日复核\"以图搜人\",InsightFace秒级回传嫌疑人身份+家庭关系+不良行为台账;\r"
    "3. 自动派治综工单+监护人短信,\"图—情—指\"5分钟闭环;\r"
    "4. 双图谱碰撞:GraphSAGE识别团伙圈层 + GraphRAG对37.8万条笔录抽取实体社区,"
    "三锚点对齐;\r"
    "5. 五维评分R=α₁家庭+α₂个人+α₃行为+α₄同伴+α₅在校+β·GraphSAGE,输出红/黄/蓝牌;\r"
    "6. 红牌触发六位一体合成处置,工单全流程留痕、回执回流模型形成自训迭代闭环。\r"
    "\r"
    "三、八大模块\r"
    "视像识别、人像合成、双图谱研判、五维评分、合成工单、模型资产、文书辅助、运维监管。"
)

SECTION_2 = (
    "一、技术架构\r"
    "五层架构(业务应用层/双图谱融合层/三引擎技术层/数据治理层/数据底座层),层间"
    "REST API+任务队列解耦。\r"
    "\r"
    "二、技术栈\r"
    "Python 3.12 + Flask 3.x + Neo4j 5.x + PyG 2.5+ + ONNX Runtime + 微软GraphRAG +"
    " Ollama + Docker 27.x,全栈100%开源、内网部署、数据不出公安网。\r"
    "\r"
    "三、关键技术\r"
    "1. 民警零基础自训YOLO26\"翘车头\"识别(★全省首例民警自训用于细分违法识别);\r"
    "2. 基层版\"图情指一体化\":YOLO → InsightFace → 治综API,响应从2天到30秒;\r"
    "3. 双图谱融合(★业内尚未广泛应用):三锚点对齐\"关系驱动+语义验证\"双重确认;\r"
    "4. 五维评分+GraphSAGE黑白盒融合(★项目独创):多库共现风险叠加业内独家;\r"
    "5. 工单化闭环+合成机制常态化:破解数字侦查\"算得出、落不下\"最后一公里;\r"
    "6. 民警自训模型资产化(★商业平台天然做不到):基层独立完成采样—标注—训练—"
    "部署全流程。\r"
    "\r"
    "四、性能与安全\r"
    "500张/分钟、YOLO准确率85%+、InsightFace秒级、5分钟闭环、AUC ≥ 0.80;全栈本地化"
    "+双层三档应急预案;同战法一键适配聚众斗殴、校园欺凌等专案,1-2周完成1个县区"
    "分局本地化部署。"
)

SECTION_3 = (
    "一、★核心成效(已实战检验)\r"
    "前身\"猎影哨兵\"2025年10月在飙车炸街专项整治专班正式投入应用:\r"
    "1. 释放专职筛图警力2名重回研判核查、嫌疑人讯问等核心工作;\r"
    "2. 累计研判卡口图片逾100万张(单机500张/分钟);\r"
    "3. \"图情指\"派单5分钟闭环(传统2-3天);\r"
    "4. 飙车警情同比降11.8%,攻坚阶段降幅37.4%;\r"
    "5. 查处违法7,692起、查处比值(攻坚期)72.3、扣车7,051辆、行政拘留437人、刑事"
    "立案8起;\r"
    "6. ★处置涉案未成年人20余名,跟踪回访零再犯。\r"
    "\r"
    "二、典型案例(脱敏)\r"
    "1. 飙车团伙串并:平台经同卡口共现自动发现7名未成年人构成\"飙车圈子\",识别1名"
    "核心组织者,启动六位一体处置,3个月回访零再犯,全流程不到4小时;\r"
    "2. 辍学未成年人红牌预警:\"辍学+单亲+同行同乘前科+频繁夜游\"四维预警,民政帮扶"
    "+社工跟进+技校就读阻断,3个月无任何涉刑警情。\r"
    "\r"
    "三、本地应用做法\r"
    "平台已成为常态化标准工具,与刑侦/交警/侦查中心/检察院未检处/教育/民政等7+部门"
    "建立数据协作,以工单链承载\"一次预警、多方接诊\",治理增量可考评、可复盘、可"
    "反哺模型。(正式申报时所有案例须经脱密审批。)"
)

SECTION_4 = (
    "聚焦\"业务-机制-技术\"三维,凝练为\"一个独具一帜切入点+三大可复制方法论+七大"
    "创新点\"。\r"
    "\r"
    "一、业务创新\r"
    "开辟\"预防未成年人违法犯罪\"数字侦查新主线;★独具一帜切入点——民警零基础自训"
    "YOLO26\"飙车炸街翘车头\"细分违法识别,在基层公安领域具有显著开创性;工作流重构"
    "发现前置≥30天、识别效率100倍、关系发现率+400%、处置分级阻断、回访闭环。\r"
    "\r"
    "二、机制创新\r"
    "\"三跨合成\"(跨警种+跨部门+跨层级)打破7部门壁垒;\"六位一体\"分级处置(训诫+教育"
    "+检察建议+民政+专门学校+监护人责令);★项目灵魂——\"工单化闭环+合成机制常态化\""
    "破解\"算得出、落不下\"最后一公里,跨部门标准动作以可审计工单链承载、岗位/时限/"
    "回执/复盘全留痕、模型反哺迭代。\r"
    "\r"
    "三、技术创新\r"
    "双图谱融合(★业内尚未广泛应用)、五维评分+GraphSAGE黑白盒融合(★独创)、"
    "YOLO26+YOLOE-26开放词表(★2026最新)、基层AI自主可控(★商业平台天然做不到)、"
    "双层三档应急预案。\r"
    "\r"
    "四、★三大可复制方法论(项目灵魂)\r"
    "①AI替代人工感知基层重复劳动阵地化模式;②基层版图情指一体化轻量整合路径;"
    "③工单化闭环+合成机制常态化破局机制——技术只是支撑方法论落地的工具。"
)

SECTION_5 = (
    "一、政策战略\r"
    "落实党的二十大\"加强未成年人保护\"与公安部\"预知预警、主动公安\"部署;契合广东"
    "省公安数字化改革三年行动及省厅2026年\"数字侦查能力测评\"AI+方向;衔接最高检"
    "\"涉罪未成年人分级处遇\"机制及《预防未成年人犯罪法》立法精神。\r"
    "\r"
    "二、推广路径(★最大推广价值)\r"
    "1. 方法论可复制:三大方法论可推广至所有基层重复性感知场景/轻量跨系统整合场景/"
    "跨部门治理留痕反哺场景;\r"
    "2. 横向案件:聚众斗殴、校园欺凌、电信诈骗低龄化、未成年人涉黄涉赌、\"两卡\"等"
    "专案均可一键复用;\r"
    "3. 纵向区域:1-2周完成1县区分局本地化部署,适配粤东西北所有地市;2026.7-12"
    "试点1区→扩展5区→沉淀全省方案,2027年全省地市级推广;\r"
    "4. 警种多点:已与刑侦/交警/侦查中心/检察院未检处/教育/民政等达成数据协作。\r"
    "\r"
    "三、综合价值\r"
    "经济:零采购、按全省21地市保守测算每年节约采购支出超千万元;学术:核心期刊1-2"
    "篇、发明专利2-3项;★社会:\"零再犯\"意味着20余个家庭避免悲剧——\"数字侦查\""
    "在\"预防未成年人违法犯罪\"命题上最具温度也最具深度的社会价值。"
)

SECTION_6 = (
    "一、原创声明\r"
    "本作品由XX市公安局治安管理支队民警自主研发,代码完整可追溯,无外包、无商业"
    "采购、无第三方系统嵌入,完全符合\"严禁直接使用商业化成品\"竞赛要求。\r"
    "\r"
    "二、自主研发证明\r"
    "1. 代码:公安内网Git完整托管,2024.10持续迭代至2026.5,后端约2.5万行Python+前端"
    "1.5万行+模型脚本0.8万行,主要模块由项目负责人独立完成;\r"
    "2. 模型自训:YOLO26自训权重(best.pt)、数据集(manifest.json)、标注样本均为民警"
    "自采、自标、自训,保留训练日志与AUC评估;\r"
    "3. 时间线:2024.10自学YOLO训出飙车识别释放2名筛图警力 → 2024.11打通InsightFace"
    " → 2024.12 Flask实战 → 2025.3治综API对接形成\"图情指\"闭环 → 2025.4获市局比武"
    "奖项 → 2026.5自学GraphRAG+GNN,升级聚焦预防未成年人主线定名「刑智·护苗」。\r"
    "\r"
    "三、佐证与自主可控\r"
    "Git提交日志可市局信通处验证;市局\"智慧公安创新项目\"比武奖项证书;飙车炸街专班"
    "/刑侦/交警实战书面佐证;YOLO26/PyG/Neo4j/GraphRAG/Gemma3/Ollama/InsightFace均"
    "为国际开源项目合规使用;计划2026.8前完成软著登记、2026年底前争取发明专利受理"
    "1-2件;代码自研+全栈本地化+数据不出公安网+基层民警可自主迭代模型,完全符合公"
    "安部\"自主可控\"要求。"
)


# ============================ 刑侦合成作战版 ============================

X_SUMMARY = (
    "针对基层公安刑侦工作中长期存在的「视频侦查阵地警力被低价值人工筛图消耗、"
    "'图—情—指'合成链路碎片化、研判产出与跨警种跨部门处置'最后一公里'断裂」"
    "三大痛点,本作品立足\"AI+合成作战\"刑侦主线,聚焦\"预防未成年人违法犯罪\""
    "命题。以全省首例民警零基础自训YOLO26\"飙车炸街翘车头\"细分违法识别为基层"
    "视像侦查独具一帜的切入点,叠加InsightFace人像卡口、Neo4j异构关系图谱、"
    "GraphSAGE团伙圈层研判、微软GraphRAG笔录串并、Gemma3-4B本地文书辅助,构建"
    "\"夜间阵地巡查—视像/人像/治综一站合成—模型自训资产化—关系网+笔录双图谱"
    "碰撞—六位一体合成处置—红黄蓝牌跟踪督办\"六大刑侦数字技战法。前身在飙车"
    "炸街专项整治中累计研判卡口图片逾100万张、释放专职筛图警力2名、警情同比降"
    "11.8%、攻坚阶段降幅37.4%、处置涉案未成年人20余名零再犯。全栈开源、零采购、"
    "内网部署、数据不出公安网,沉淀三项可向全省基层刑侦推广的合成作战方法论。"
)

X_SECTION_1 = (
    "一、运行环境\r"
    "公安私有云本地化部署、数据不出公安网。治安/刑侦支队现有i5+16GB+4GB显存工作站"
    "即可承载;Python+Flask+Neo4j+Docker+Ollama;模型栈含YOLO26/YOLOE-26/InsightFace/"
    "GraphSAGE/微软GraphRAG/Gemma3-4B;数据底座贯通公安(警情/案件/笔录/5,385万人像"
    "卡口轨迹)+教育/民政/卫健/残联/法院/检察/信访共8+部门2.4亿+条。\r"
    "\r"
    "二、操作步骤(以飙车炸街涉未成年人合成战为例)\r"
    "1. 阵地巡查:民警在\"卡口阵地\"框选时段+卡口,夜间YOLO26自动批量推理(500张/"
    "分钟)沉淀证据包;\r"
    "2. 视像-人像合成研判:\"以图搜人\"InsightFace比对5,385万人像轨迹库,秒级确认"
    "嫌疑人身份;\r"
    "3. 一站合成派单:自动派治综工单+监护人短信,\"图情指\"5分钟闭环;\r"
    "4. 双图谱关系研判:GraphSAGE识别\"飙车圈子\"\"校园欺凌团伙\"+GraphRAG笔录串并,"
    "三锚点对齐;\r"
    "5. 五维评分+红黄蓝牌:复合评分输出红/黄/蓝牌,红牌触发合成专班六位一体处置,"
    "工单全留痕、回执限时回流;\r"
    "6. 模型自训资产化:形成\"阵地巡查—合成研判—处置—沉淀—迭代\"刑侦数字技战法闭环。\r"
    "\r"
    "三、八大模块\r"
    "视像识别、人像合成、双图谱研判、五维评分、合成工单、模型资产、文书辅助、运维"
    "监管(红黄蓝牌跟踪督办看板)。"
)

X_SECTION_2 = (
    "一、技术架构\r"
    "五层架构(业务应用层/双图谱融合层/三引擎技术层/数据治理层/数据底座层),REST API"
    "+任务队列解耦。\r"
    "\r"
    "二、技术栈\r"
    "Python 3.12 + Flask 3.x + Neo4j 5.x + PyG 2.5+ + ONNX Runtime + 微软GraphRAG +"
    " Ollama + Docker 27.x,全栈100%开源、内网部署。\r"
    "\r"
    "三、关键技术\r"
    "1. 视像侦查阵地化——民警1.2万张样本自训YOLO26\"翘车头\",实战准确率85%+,工作站"
    "CPU可推理(★全省首例民警零基础自训用于细分违法识别);\r"
    "2. 基层版\"合成作战图情指一体化\":YOLO→InsightFace本地人像比对→治综API派单,"
    "响应从2天到30秒;\r"
    "3. 双图谱关系研判(★业内尚未广泛应用):三锚点对齐\"关系驱动+语义验证\"双重确认;\r"
    "4. 五维评分+GraphSAGE融合(★项目独创):多库共现风险叠加业内独家;\r"
    "5. 红黄蓝牌跟踪督办(★项目灵魂):研判产出固化为可审计工单,破解刑侦数字侦查"
    "\"算得出、落不下\"最后一公里;\r"
    "6. 民警自训模型资产化(★商业平台天然做不到):基层独立完成采样—标注—训练—部署。\r"
    "\r"
    "四、指标与安全\r"
    "500张/分钟、准确率85%+、InsightFace秒级、5分钟闭环、AUC ≥ 0.80;全栈本地化+"
    "笔录脱敏+双层三档应急预案+一键适配多类专案。"
)

X_SECTION_3 = (
    "一、★核心成效(已实战检验)\r"
    "前身\"猎影哨兵\"2025年10月在飙车炸街专项整治专班投入应用:\r"
    "1. 释放专职筛图警力2名重回研判核查、嫌疑人讯问等刑侦核心活动;\r"
    "2. 累计研判卡口图片逾100万张(500张/分钟);\r"
    "3. 合成派单5分钟闭环(传统2-3天);\r"
    "4. 飙车炸街警情同比降11.8%,攻坚阶段降幅37.4%;\r"
    "5. 查处违法7,692起、查处比值(攻坚期)72.3、扣车7,051辆、行政拘留437人、刑事"
    "立案8起;\r"
    "6. ★处置涉案未成年人20余名,跟踪回访零再犯。\r"
    "\r"
    "二、典型案例(脱敏)\r"
    "1. 飙车团伙串并案:平台经同卡口共现自动发现7名未成年人构成\"飙车圈子\",经介数"
    "中心度识别1名核心组织者,合成专班启动六位一体处置,3个月回访零再犯;\r"
    "2. 校园欺凌团伙串并:平台Louvain社区发现+GraphRAG笔录摘要双图谱碰撞,在3起独立"
    "\"轻微肢体冲突\"中识别同一社区子图、笔录\"老大\"\"小弟\"角色,联动法治副校长进"
    "校园专项干预。\r"
    "\r"
    "三、本地应用做法\r"
    "平台已成为常态化合成作战工具,跨警种+跨部门+跨层级,以\"红黄蓝牌跟踪督办\"工单"
    "链承载预警落地,治理增量可考评、可复盘、可反哺模型。(正式申报时所有案例须经"
    "脱密审批。)"
)

X_SECTION_4 = (
    "立足\"AI+合成作战\"刑侦视角,凝练为\"一个独具一帜切入点+三大可复制方法论+七大"
    "创新点\"。\r"
    "\r"
    "一、业务创新\r"
    "开辟\"预防未成年人违法犯罪\"刑侦数字侦查新主线,让\"未来案件\"在还没成案前被"
    "消解;★独具一帜切入点——民警零基础自训YOLO26\"飙车炸街翘车头\"细分违法识别,"
    "在基层公安具有显著开创性;工作流重构发现前置≥30天、识别效率100倍、关系发现率"
    "+400%、处置分级阻断、回访闭环。\r"
    "\r"
    "二、机制创新\r"
    "\"三跨合成\"(跨警种+跨部门+跨层级)打破7部门壁垒;\"六位一体\"分级合成处置打破"
    "\"训诫即终结\";★项目灵魂——\"红黄蓝牌跟踪督办+合成机制常态化\"破解刑侦数字"
    "侦查\"算得出、落不下\"最后一公里;首创\"侦查中心大模型推理资源共建共用机制\"。\r"
    "\r"
    "三、技术创新\r"
    "双图谱关系研判融合(★业内尚未广泛应用)、五维评分+多库共现风险叠加(★独创)、"
    "YOLO26+YOLOE-26(★2026最新)、基层AI自主可控(★商业平台天然做不到)、双层三档"
    "应急预案。\r"
    "\r"
    "四、★三大可复制方法论(项目灵魂)\r"
    "①AI替代人工感知基层视像侦查阵地化运行模式;②基层版合成作战图情指一体化轻量"
    "实现路径;③红黄蓝牌跟踪督办+合成机制常态化破局机制。"
)

X_SECTION_5 = (
    "一、政策战略\r"
    "落实党的二十大\"加强未成年人保护\"与公安部\"以情况预知预警实现公安工作主动\";"
    "契合广东省公安数字化改革三年行动及省厅2026年刑侦\"数字侦查能力测评\"AI+方向;"
    "衔接最高检\"涉罪未成年人分级处遇\"机制及《预防未成年人犯罪法》立法精神;契合"
    "公安部\"AI+公安政务/数字侦查/合成作战/基层技术革新\"建设方向。\r"
    "\r"
    "二、推广路径(★最大推广价值)\r"
    "1. 方法论可复制:三大方法论可推广至所有基层重复性感知场景/轻量跨系统整合场景/"
    "跨部门接诊闭环场景;\r"
    "2. 横向案件:聚众斗殴、校园欺凌、电信诈骗低龄化、未成年人涉黄涉赌、\"两卡\"等"
    "专案均可一键复用;\r"
    "3. 纵向区域:1-2周完成1县区分局本地化部署,适配粤东西北所有地市基层刑侦;2026.7"
    "-12试点1区→扩展5区→沉淀全省方案,2027年全省地市级推广;\r"
    "4. 警种多点:已与刑侦、交警、侦查中心、检察院未检处、教育/民政等达成数据协作。\r"
    "\r"
    "三、综合价值\r"
    "经济:零采购、按全省21地市保守测算每年节约采购支出超千万元;学术:核心期刊1-2"
    "篇、发明专利2-3项;★社会:\"零再犯\"意味着20余家庭避免悲剧——\"数字侦查\"在"
    "\"预防未成年人违法犯罪\"刑侦命题上最具温度也最具深度的社会价值。"
)

X_SECTION_6 = (
    "一、原创声明\r"
    "本作品由XX市公安局治安管理支队民警自主研发,代码完整可追溯,无外包、无商业"
    "采购、无第三方系统嵌入,完全符合\"严禁直接使用商业化成品\"竞赛要求。\r"
    "\r"
    "二、自主研发证明\r"
    "1. 代码:公安内网Git完整托管,2024.10持续迭代至2026.5,后端约2.5万行Python+前端"
    "1.5万行+模型脚本0.8万行,主要模块由项目负责人独立完成;\r"
    "2. 模型自训:YOLO26\"翘车头/未戴头盔/多人搭乘\"自训权重(best.pt)、数据集"
    "(manifest.json)、标注样本均为民警自采、自标、自训,保留训练日志与AUC评估;\r"
    "3. 时间线:2024.10自学YOLO训出飙车识别释放2名筛图警力 → 2024.11打通InsightFace"
    " → 2024.12 Flask实战 → 2025.3治综API对接形成\"图情指\"闭环 → 2025.4获市局比武"
    "奖项 → 2025年底提出\"红黄蓝牌跟踪督办+合成机制常态化\" → 2026.5自学GraphRAG+"
    "GNN,升级聚焦预防未成年人主线定名「刑智·护苗」。\r"
    "\r"
    "三、佐证与自主可控\r"
    "Git提交日志可市局信通处验证;市局\"智慧公安创新项目\"比武奖项证书;飙车炸街专班"
    "/刑侦/交警实战书面佐证;YOLO26/PyG/Neo4j/GraphRAG/Gemma3/Ollama/InsightFace均"
    "为国际开源项目合规使用;计划2026.8前完成软著登记、2026年底前争取发明专利受理"
    "1-2件;代码自研+全栈本地化+数据不出公安网+模型迭代能力自主(基层独立完成全流"
    "程),符合公安部\"自主可控\"要求。"
)


# ----------------------------- 公文格式工具 -----------------------------

def _detect_level(text):
    """根据段落首部模式判断公文层级:
    1=一级(黑体三号), 2=二级(楷体_GB2312三号),
    3=三级(仿宋_GB2312三号加粗), 0=正文。"""
    t = (text or "").lstrip("\ufeff").strip()
    if not t:
        return 0
    if H1_RE.match(t):
        return 1
    if H2_RE.match(t):
        return 2
    if H3_RE.match(t):
        return 3
    return 0


def apply_paragraph_format(para, force_level=None):
    """对单个段落套用公文格式(字体/字号/加粗/行距/首行缩进)。
    空段落自动收紧为 12 磅(视觉换行但不浪费纸面),内容段保持 28 磅公文行距。"""
    text = para.Range.Text or ""
    has_content = bool(text.strip())
    level = force_level if force_level is not None else _detect_level(text)
    rng = para.Range
    try:
        rng.Font.Size = SAN_HAO_PT
        rng.Font.NameAscii = "Times New Roman"
        rng.Font.NameOther = "Times New Roman"
    except Exception:
        pass
    if level == 1:
        rng.Font.NameFarEast = "黑体"
        rng.Font.Bold = False
    elif level == 2:
        rng.Font.NameFarEast = "楷体_GB2312"
        rng.Font.Bold = False
    elif level == 3:
        rng.Font.NameFarEast = "仿宋_GB2312"
        rng.Font.Bold = True
    else:
        rng.Font.NameFarEast = "仿宋_GB2312"
        rng.Font.Bold = False
    try:
        pf = para.Format
        pf.LineSpacingRule = WD_LINE_SPACE_EXACTLY
        pf.LineSpacing = LINE_SPACING_PT if has_content else 12
        pf.SpaceBefore = 0
        pf.SpaceAfter = 0
        pf.Alignment = WD_ALIGN_LEFT
        pf.PageBreakBefore = 0
        pf.KeepWithNext = 0
        pf.WidowControl = 0
        if level == 0 and has_content:
            pf.FirstLineIndent = FIRST_LINE_INDENT_PT
        else:
            pf.FirstLineIndent = 0
    except Exception:
        pass


def set_cell_text(cell, text, asian_font=None, latin_font=None,
                  auto_format=False, force_level=None):
    """设置单元格文本内容;\\r 视作段落分隔。
    auto_format=True 按公文格式逐段排版;
    force_level 强制某一层级(用于(一)..(六)表头);
    asian_font/latin_font 用于绕过自动格式直接指定字体(checkbox单元格)。"""
    text = text.replace("\r\n", "\r").replace("\n", "\r")
    rng = cell.Range
    rng.Text = text
    if auto_format or force_level is not None:
        for para in cell.Range.Paragraphs:
            apply_paragraph_format(para, force_level=force_level)
    if asian_font:
        try:
            rng.Font.NameFarEast = asian_font
        except Exception:
            pass
    if latin_font:
        try:
            rng.Font.NameAscii = latin_font
            rng.Font.NameOther = latin_font
        except Exception:
            pass


# ----------------------------- 填表执行 -----------------------------

STANDALONE_TITLES = {"一、基本信息表", "二、主创人员表", "三、作品内容"}
SECTION_HEADERS = [
    "(一)功能介绍", "(二)技术方案与实现", "(三)实战成效",
    "(四)创新亮点", "(五)推广前景", "(六)原创证明",
]


def fill_doc(src_path, out_path, summary, sections, label):
    """打开模板,按 summary/sections 填充,套公文格式后另存为 out_path。
    每次都启动独立 Word 实例,避免连续两次 Documents.Open 触发 COM RPC 异常。"""
    print(f"\n========== 生成 [{label}] -> {out_path} ==========", flush=True)
    word = win32com.client.gencache.EnsureDispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    doc = word.Documents.Open(src_path, ReadOnly=False, AddToRecentFiles=False)
    try:
        tables = doc.Tables
        print(f"[INFO] 文档共 {tables.Count} 张表,逐一填写。", flush=True)

        # 封面表
        t1 = tables.Item(1)
        set_cell_text(t1.Cell(1, 2), PROJECT_NAME)
        set_cell_text(t1.Cell(2, 2), MAIN_CREATOR)
        set_cell_text(t1.Cell(3, 2), APPLICANT_UNIT)
        print("[OK] 封面表已填写。", flush=True)

        # 基本信息表
        t2 = tables.Item(2)
        set_cell_text(t2.Cell(1, 2), PROJECT_NAME)
        set_cell_text(t2.Cell(2, 2), APPLICANT_UNIT)
        set_cell_text(t2.Cell(3, 3), MAIN_CREATOR)
        set_cell_text(t2.Cell(3, 5), PARTICIPANTS)
        set_cell_text(t2.Cell(4, 2), APPLICATION_SCENARIO, asian_font="宋体")
        set_cell_text(t2.Cell(5, 2), PRODUCT_FORM, asian_font="宋体")
        set_cell_text(t2.Cell(7, 1), summary, auto_format=True)
        print("[OK] 基本信息表已填写。", flush=True)

        # 主创人员表留空
        print("[SKIP] 主创人员表保留空白(等用户补充姓名/职务/警号/电话)。",
              flush=True)

        # 三、作品内容六大节
        for i, body in enumerate(sections):
            tbl = tables.Item(4 + i)
            for para in tbl.Cell(1, 1).Range.Paragraphs:
                apply_paragraph_format(para, force_level=2)
            set_cell_text(tbl.Cell(2, 1), body, auto_format=True)
            print(f"[OK] {SECTION_HEADERS[i]} 已填写并套用公文格式。", flush=True)

        # 文档正文中独立标题(非表格内)
        # Word 在大量表格写入后可能短暂忙(RPC_E_CALL_REJECTED),用 _retry_com 兜底
        paras = _retry_com(lambda: doc.Paragraphs)
        count = _retry_com(lambda: paras.Count)
        # 第一遍:标记前4张表(封面/基本信息/主创人员)所在范围,保留其页面边界;
        # 第二遍:格式化独立标题,并清除"三、作品内容"之后所有段落的强制换页/段前分页,
        #         让(一)~(六)六节正文表自然顺排,而非每节独占新页。
        t3_end = _retry_com(lambda: doc.Tables.Item(3).Range.End)
        for i in range(1, count + 1):
            p = _retry_com(lambda: paras.Item(i))
            t = (_retry_com(lambda: p.Range.Text) or "").strip().rstrip("\r")
            if t in STANDALONE_TITLES:
                _retry_com(lambda: apply_paragraph_format(p, force_level=1))
            # 清除主创人员表之后所有段落的 PageBreakBefore,让六大正文表顺排
            try:
                if _retry_com(lambda: p.Range.Start) >= t3_end:
                    _retry_com(lambda: setattr(p.Format, "PageBreakBefore", 0))
            except Exception:
                pass
        print("[OK] 文档独立标题段已按一级标题格式化,六节正文表已设为顺排。",
              flush=True)

        if os.path.exists(out_path):
            os.remove(out_path)
        doc.SaveAs2(out_path, FileFormat=0)
        print(f"[DONE] 输出文件:{out_path}", flush=True)
    finally:
        try:
            doc.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            word.Quit()
        except Exception:
            pass


def main():
    if not os.path.exists(SRC):
        print(f"[ERR] 源文件不存在:{SRC}", flush=True)
        sys.exit(1)

    pythoncom.CoInitialize()
    try:
        fill_doc(
            SRC, OUT_M,
            summary=SUMMARY,
            sections=[SECTION_1, SECTION_2, SECTION_3,
                      SECTION_4, SECTION_5, SECTION_6],
            label="方法论版",
        )
        fill_doc(
            SRC, OUT_X,
            summary=X_SUMMARY,
            sections=[X_SECTION_1, X_SECTION_2, X_SECTION_3,
                      X_SECTION_4, X_SECTION_5, X_SECTION_6],
            label="刑侦合成作战版",
        )
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
