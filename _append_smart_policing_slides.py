import json
import struct
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PRESENTATION_ID = "11z8XEUpse-MfhrPnyuOz7WvQ9Oe-H0VxkNIgNh8mCKQ"
CRED_PATH = Path(r"C:\Users\So\.google_workspace_mcp\credentials\gaofenglongshao@gmail.com.json")
IMAGE_DIR = Path(r"C:\Users\So\Desktop\project\multi-rider\screenshots")

PAGE_W = 9144000
PAGE_H = 5143500

COLORS = {
    "bg": {"red": 0.95686275, "green": 0.96862745, "blue": 0.9843137},
    "navy": {"red": 0.07058824, "green": 0.19215687, "blue": 0.2901961},
    "gold": {"red": 0.78431374, "green": 0.63529414, "blue": 0.29803923},
    "card": {"red": 1, "green": 1, "blue": 1},
    "text_dark": {"red": 0.05882353, "green": 0.09019608, "blue": 0.16470589},
    "text_muted": {"red": 0.19215687, "green": 0.27450982, "blue": 0.37254903},
    "badge_text": {"red": 0.05882353, "green": 0.14117648, "blue": 0.21568628},
}

IMAGES = {
    "01-login.png": "https://drive.google.com/uc?export=view&id=1Rxy96HqdWlcDbGQ8koJES9cpyYaVIlnp",
    "02-data-detection-top.png": "https://drive.google.com/uc?export=view&id=12gaXTAnTPbp2sYfUP-jcolYy6YzsPxSl",
    "03-data-detection-bottom.png": "https://drive.google.com/uc?export=view&id=1kOeJFw5MDObA9CHMCF8-lbKwNwuBDIEC",
    "04-onsite-material-analysis.png": "https://drive.google.com/uc?export=view&id=1duqjDmG4EFoAmxoQ4MbkYE95XYifi_0s",
    "05-face-recognition-verification.png": "https://drive.google.com/uc?export=view&id=1Mka0KoHeycJnT2KYcc_-tEk7acap9uPz",
    "06-model-self-training.png": "https://drive.google.com/uc?export=view&id=1XrSTIGYfnEBK7ZHSPKlSCE-VDgbbNCsm",
    "07-task-dispatch-top.png": "https://drive.google.com/uc?export=view&id=1NClLxp25wixCoQJG7sGl7DY6moOwc5VC",
    "08-task-dispatch-bottom.png": "https://drive.google.com/uc?export=view&id=18vv2gz-Zw3ToJ2eecR5zEog9dq4wibNV",
}

SLIDES = [
    {
        "id": "append_overview_20260328",
        "badge": "追加页",
        "title": "项目总览与工作台入口",
        "tech_title": "项目概述",
        "tech_body": "本系统面向基层警务实战，围绕海量图片筛查、本地素材研判、身份核验、模型迭代和任务流转，建设统一工作台。登录页展示了平台集中化入口，便于各模块能力在同一界面下协同运行。",
        "value_title": "核心价值",
        "value_body": "项目强调从发现、研判、核验到处置的闭环贯通，让机器完成高重复筛查，让民警聚焦复核与处置，提升线索发现效率和后续流转质量。",
        "images": ["01-login.png"],
    },
    {
        "id": "append_module1_20260328",
        "badge": "模块一",
        "title": "数据检测与研判",
        "tech_title": "功能说明",
        "tech_body": "系统可按时间范围批量拉取二轮车图片，并调用专项模型或开放词表模型自动筛查命中结果。顶部和底部界面分别展示任务配置、命中结果浏览及后续导出整理流程。",
        "value_title": "实战价值",
        "value_body": "该模块把人工逐张翻看的工作前移为系统自动初筛，能够在短时间内从海量图片中压缩出重点线索，显著降低人工工作量，提升专项整治效率。",
        "images": ["02-data-detection-top.png", "03-data-detection-bottom.png"],
    },
    {
        "id": "append_module2_20260328",
        "badge": "模块二",
        "title": "本地素材研判",
        "tech_title": "功能说明",
        "tech_body": "本模块支持上传压缩图片和视频素材，自动抽帧后进入统一识别流程。界面体现了素材接入、批量推理和结果回传的一体化处理能力。",
        "value_title": "实战价值",
        "value_body": "面对执法记录仪、现场取证和群众举报素材，系统可以替代人工反复播放、暂停、截图和逐帧查看，帮助民警更快锁定关键画面与重点对象。",
        "images": ["04-onsite-material-analysis.png"],
    },
    {
        "id": "append_module3_20260328",
        "badge": "模块三",
        "title": "人脸识别与人员核验",
        "tech_title": "功能说明",
        "tech_body": "系统在前序检测结果基础上，自动提取有效人脸并与人脸库进行相似度比对，输出候选身份信息，同时支持人脸库同步、增量更新和重建管理。",
        "value_title": "实战价值",
        "value_body": "该模块打通了从行为线索发现到身份核验的关键环节，减少多系统切换和人工比对成本，让后续任务派发具备更完整、更结构化的身份依据。",
        "images": ["05-face-recognition-verification.png"],
    },
    {
        "id": "append_module4_20260328",
        "badge": "模块四",
        "title": "模型自训练",
        "tech_title": "功能说明",
        "tech_body": "模块围绕数据集管理、自动标注、训练任务调度、模型注册和槽位切换构建训练闭环，可将前序实战结果回流为训练数据，持续优化专项模型。",
        "value_title": "实战价值",
        "value_body": "系统不再依赖一次性训练的固定模型，而是形成“实战产生数据、数据反哺模型、模型再服务实战”的持续学习机制，使平台能力更贴近本地业务场景。",
        "images": ["06-model-self-training.png"],
    },
    {
        "id": "append_module5_20260328",
        "badge": "模块五",
        "title": "任务下发",
        "tech_title": "功能说明",
        "tech_body": "系统将识别与核验结果整理为待派发任务，支持预览、自动推送和短信提醒。两张界面分别体现待派发列表管理和任务详情流转能力。",
        "value_title": "实战价值",
        "value_body": "该模块解决了线索发现后的“最后一公里”问题，把识别、核验和派发贯通为标准化流水线，减少人工整理和重复录入带来的时间损耗与信息遗漏。",
        "images": ["07-task-dispatch-top.png", "08-task-dispatch-bottom.png"],
    },
]


def load_creds():
    info = json.loads(CRED_PATH.read_text(encoding="utf-8"))
    creds = Credentials.from_authorized_user_info(info, scopes=info.get("scopes"))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        CRED_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def emu_fit_box(img_path: Path, box_w: int, box_h: int):
    with img_path.open("rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Unsupported image format for {img_path}")
        chunk_len = struct.unpack(">I", f.read(4))[0]
        chunk_type = f.read(4)
        if chunk_type != b"IHDR" or chunk_len < 8:
            raise ValueError(f"Invalid PNG header for {img_path}")
        w, h = struct.unpack(">II", f.read(8))
    scale = min(box_w / w, box_h / h)
    return int(w * scale), int(h * scale)


def create_shape(reqs, object_id, shape_type, x, y, w, h, fill=None, radius=False):
    reqs.append(
        {
            "createShape": {
                "objectId": object_id,
                "shapeType": shape_type,
                "elementProperties": {
                    "pageObjectId": current_slide_id,
                    "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                    "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"},
                },
            }
        }
    )
    if fill is not None:
        reqs.append(
            {
                "updateShapeProperties": {
                    "objectId": object_id,
                    "shapeProperties": {
                        "shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": fill}}},
                        "outline": {"propertyState": "NOT_RENDERED"},
                    },
                    "fields": "shapeBackgroundFill.solidFill.color,outline.propertyState",
                }
            }
        )


def create_textbox(reqs, object_id, x, y, w, h, text, font_size, color, bold=False, align="START"):
    create_shape(reqs, object_id, "TEXT_BOX", x, y, w, h, fill=None)
    reqs.append({"insertText": {"objectId": object_id, "insertionIndex": 0, "text": text}})
    reqs.append(
        {
            "updateTextStyle": {
                "objectId": object_id,
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": color}},
                    "fontFamily": "Noto Sans SC",
                    "fontSize": {"magnitude": font_size, "unit": "PT"},
                    "bold": bold,
                },
                "textRange": {"type": "ALL"},
                "fields": "foregroundColor,fontFamily,fontSize,bold",
            }
        }
    )
    reqs.append(
        {
            "updateParagraphStyle": {
                "objectId": object_id,
                "style": {"alignment": align, "lineSpacing": 115},
                "textRange": {"type": "ALL"},
                "fields": "alignment,lineSpacing",
            }
        }
    )


def create_image(reqs, object_id, page_id, image_name, x, y, box_w, box_h):
    img_path = IMAGE_DIR / image_name
    width, height = emu_fit_box(img_path, box_w, box_h)
    tx = x + (box_w - width) // 2
    ty = y + (box_h - height) // 2
    reqs.append(
        {
            "createImage": {
                "objectId": object_id,
                "url": IMAGES[image_name],
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {
                        "width": {"magnitude": width, "unit": "EMU"},
                        "height": {"magnitude": height, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": tx,
                        "translateY": ty,
                        "unit": "EMU",
                    },
                },
            }
        }
    )


creds = load_creds()
drive = build("drive", "v3", credentials=creds)
slides = build("slides", "v1", credentials=creds)
presentation = slides.presentations().get(presentationId=PRESENTATION_ID).execute()
slide_count = len(presentation.get("slides", []))

requests = []

for idx, slide in enumerate(SLIDES):
    current_slide_id = slide["id"]
    requests.append(
        {
            "createSlide": {
                "objectId": current_slide_id,
                "insertionIndex": slide_count + idx,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }
        }
    )

    create_shape(requests, f"{current_slide_id}_bg", "RECTANGLE", 0, 0, PAGE_W, PAGE_H, fill=COLORS["bg"])
    create_shape(requests, f"{current_slide_id}_top", "RECTANGLE", 0, 0, PAGE_W, 685800, fill=COLORS["navy"])
    create_shape(requests, f"{current_slide_id}_badge", "ROUND_RECTANGLE", 431800, 914400, 990600, 304800, fill=COLORS["gold"])
    create_textbox(
        requests,
        f"{current_slide_id}_badge_text",
        558800,
        952500,
        736500,
        203100,
        slide["badge"],
        11,
        COLORS["badge_text"],
        bold=True,
        align="CENTER",
    )
    create_textbox(
        requests,
        f"{current_slide_id}_title",
        1600200,
        876300,
        5600000,
        355600,
        slide["title"],
        24,
        COLORS["text_dark"],
        bold=True,
    )

    create_shape(requests, f"{current_slide_id}_tech_card", "ROUND_RECTANGLE", 431800, 1524000, 3124200, 1231900, fill=COLORS["card"])
    create_textbox(
        requests,
        f"{current_slide_id}_tech_title",
        609600,
        1701800,
        2200000,
        160000,
        slide["tech_title"],
        16,
        COLORS["text_dark"],
        bold=True,
    )
    create_textbox(
        requests,
        f"{current_slide_id}_tech_body",
        609600,
        2020000,
        2500000,
        610000,
        slide["tech_body"],
        12,
        COLORS["text_muted"],
    )

    create_shape(requests, f"{current_slide_id}_value_card", "ROUND_RECTANGLE", 431800, 2960000, 3124200, 1320000, fill=COLORS["card"])
    create_textbox(
        requests,
        f"{current_slide_id}_value_title",
        609600,
        3138000,
        2200000,
        160000,
        slide["value_title"],
        16,
        COLORS["text_dark"],
        bold=True,
    )
    create_textbox(
        requests,
        f"{current_slide_id}_value_body",
        609600,
        3456000,
        2500000,
        720000,
        slide["value_body"],
        12,
        COLORS["text_muted"],
    )

    create_shape(requests, f"{current_slide_id}_image_card", "ROUND_RECTANGLE", 4040000, 1524000, 4660000, 2900000, fill=COLORS["card"])

    if len(slide["images"]) == 1:
        create_image(requests, f"{current_slide_id}_image_1", current_slide_id, slide["images"][0], 4220000, 1700000, 4300000, 2550000)
    else:
        create_image(requests, f"{current_slide_id}_image_1", current_slide_id, slide["images"][0], 4200000, 1660000, 4300000, 1180000)
        create_image(requests, f"{current_slide_id}_image_2", current_slide_id, slide["images"][1], 4200000, 2960000, 4300000, 1180000)

result = slides.presentations().batchUpdate(
    presentationId=PRESENTATION_ID, body={"requests": requests}
).execute()

summary = {
    "presentationId": PRESENTATION_ID,
    "createdSlides": [s["id"] for s in SLIDES],
    "replies": len(result.get("replies", [])),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
