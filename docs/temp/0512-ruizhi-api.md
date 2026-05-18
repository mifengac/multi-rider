主体功能说明
模型功能：支持查询模型列表，查询模型明细；
文件功能：支持文件上传，文件删除，文件列表检索，文件信息检索，文件内容获取；支持文件在用户间隔离；
知识库功能：支持知识库创建，知识库删除，知识库列表检索，知识库明细检索，知识库信息修改，知识库用户间分享，知识库重置知识库与文件间的关联创建、删除、列表、明细功能；支持知识库在用户间隔离；
向量功能：支持1024字节向量生成
音频功能：支持文转音（TTS），实时音转文（ASR），音频翻译；
会话功能：支持流式/非流式大模型的会话，支持@的知识库引用；
接口标准：参考OpenAI的接口标准，细节以文档中接口的描述说明为准，未说明的请联系锐安管理员确认。
关键参数说明
BASE_URL : https://10.2.164.106/v2
API_KEY : "锐智AI服务平台->个人中心->APIKEY管理"中获取。用于接口使用方的授权识别，所有接口在调用时都会在请求头中携带。
project : 应用方自身的项目标识，联系锐安管理员申请。未申请到时，使用自有应用英文的简称。
调用示例说明
接口会包含curl、python调用两种示例。
python示例，在存在相对应的openai的接口时，只提供对应openai的调用示例。不存在时提供request的调用示例。
调用示例，默认以BASE_URL为HTTP协议示例。
调用示例，针对HTTPS协议，可参考如下方式处理：
curl：可使用 -k 选项，忽略证书验证
复制
   curl -s  -k "https://172.24.1.66:8081/v2/models" -H "Authorization: Bearer $API_KEY"
1
python - openai：可创建自定义客户端，忽略证书验证
复制
  import httpx
  client = openai.Client(api_key=API_KEY, base_url=BASE_URL, http_client=httpx.Client(verify=False))
1
2
python - request：可传递verify参数，忽略证书验证
复制
  response = requests.post(url, data=json.dumps(params), headers=headers, verify=False)
1
调用示例，其内使用的模型名称，需要在"模型列表检索"中获取到当然环境现在激活的模型。示例中统一使用ayenaspring-pro-001, ayenaaudio-001, ayenavisual-001, ayenaembedding-001进行示意。
调用示例，基于不同情况，调用返回的结果各不相同，甚至会出现异常。参考OpenAI的官方示例，本文档不再提供打印输出示例。如有需要，可申请试用环境，测试具体输出。
调用响应，通过HTTP协议实现，响应状态码同HTTP的响应码保持一致。详情可见附录
服务端点 Endpoints
模型（Models）管理
GET 模型列表检索（List）
GET ${BASE_URL}/models

列出当前可用的型号，并提供每个型号的基本信息，例如所有者和创建时间。
调用示例中的模型名称，需要在这个列表中包含下面。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ object	string	是	对象类型：list
+ data	[object]	否	
++ id	string	是	模型的ID
++ object	string	是	模型类型：model
++ created	integer	是	模型创建的时间戳
++ owned_by	string	是	模型归属的组织
++ description	string	是	模型的具体描述
++ context_length	integer	是	模型的上下文长度
++ max_input	integer	是	模型的最大输入大小
++ max_output	integer	是	模型的最大输出大小
++ tools	boolean	是	模型默认是否支持工具函数
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/models \
  -H "Authorization: Bearer $API_KEY"
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)

client.models.list()
1
2
3
4
请求体示例
无
响应体示例
复制
{
  "object": "list",
  "data": [
    {
      "created": 1686987175,
      "id": "ayenaspring-pro-001",
      "object": "model",
      "owned_by": "bjrun",
      "description": "锐安的720亿参数的大语言模型",
      "context_length": 131072,
      "max_input": 128000,
      "max_output": 6144,
      "tools": false
    },
    ...由于示例而省略部分内容...
    {
      "created": 1731902225,
      "id": "ayenaspring-advanced-001",
      "object": "model",
      "owned_by": "brurn",
      "context_length": 32000,
      "max_input": 30000,
      "max_output": 2000,
      "tools": false
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
GET 模型信息检索（Retrieve）
GET /models/{modelid}

检索模型实例，提供有关模型的基本信息，例如所有者和创建时间。
请求参数说明
名称	位置	类型	必选	说明
modelid	path	string	是	用于此请求的模型的 ID
Authorization	header	string	否	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ id	string	是	模型的ID
+ object	string	是	模型类型：model
+ created	integer	是	模型创建的时间
+ owned_by	string	是	模型归属的组织
+ description	string	是	模型的具体描述
+ context_length	integer	是	模型的上下文长度
+ max_input	integer	是	模型的最大输入大小
+ max_output	integer	是	模型的最大输出大小
+ tools	boolean	是	模型默认是否支持工具函数
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/models/ayenaspring-pro-001 \
  -H "Authorization: Bearer $API_KEY"
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)

client.models.retrieve("ayenaspring-pro-001")
1
2
3
4
请求体示例
无
响应体示例
复制
{
  "created": 1686987175,
  "id": "ayenaspring-pro-001",
  "object": "model",
  "owned_by": "bjrun",
  "description": "锐安的720亿参数的大语言模型",
  "context_length": 131072,
  "max_input": 128000,
  "max_output": 6144,
  "tools": false
}
1
2
3
4
5
6
7
8
9
10
11
文件（Files）管理
POST 文件上传接口（Upload）
POST /files

上传平台上使用的文件。目前主要是知识库使用。
单个文件的大小最大为10MB（磁盘存储字节大小）。大文件需要进行拆分后上传。
如需要一次性上传超10M的文件，请联系管理员。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
body				请求体
+ file	body	file	是	上传文件对象
+ purpose	body	string	否	上传文件的预期目的。默认值是文件上传存储
响应参数说明
名称	类型	必填	说明
body			响应体
+ id	string	是	文件标识符，可以在API端点中引用。
+ object	string	是	对象类型：file
+ bytes	integer	是	文件的大小，以字节为单位。
+ created_at	integer	是	创建文件时的Unix时间戳（以秒为单位）。
+ filename	string	是	文件名称
+ purpose	string	是	文件的预期目的的文字简要说明。
+ owner	string	是	文件的所属用户ID。
+ status	string	是	传返回的状态码。
+ status_details	string	是	上传返回的状态码说明。
调用示例
代码示例
shell示例代码
复制
curl -s -X POST ${BASE_URL}/files \
  -H "Authorization: Bearer $API_KEY" \
  -F purpose="kbs" \
  -F file="@resource/法律常识.txt"
1
2
3
4
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY,base_url=BASE_URL)
client.files.create(
  file=open("resource/法律常识.txt", "rb"),
  purpose="kbs"
)
1
2
3
4
5
6
请表单示例
复制
file: "法律常识.txt"    #根据路径加载的文件对象
purpose: kbs
1
2
响应体示例
复制
{
  "id": "file-c5a6e29a8ac648ab9f5162f6b010bb3c",
  "bytes": 10761,
  "created_at": 1735298816,
  "owner": "1",
  "filename": "法律常识.txt",
  "object": "file",
  "purpose": "kbs",
  "status": "200",
  "status_details": "文件上传成功！"
}
1
2
3
4
5
6
7
8
9
10
11
GET 文件列表检索（List）
GET /files

返回上传的文件的信息列表
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ object	string	是	对象类型：list
+ data	[object]	是	
++ id	string	是	文件标识符。
++ object	string	是	对象类型：file
++ bytes	integer	是	文件的大小，以字节为单位。
++ created_at	integer	是	创建文件时的Unix时间戳（以秒为单位）。
++ filename	string	是	文件名称
++ purpose	string	是	文件的预期目的
++ owner	string	是	文件的所属用户ID。
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/files \
  -H "Authorization: Bearer $API_KEY"
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
client.files.list()
1
2
3
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "查询文件列表成功", 
  "data": [
    {
      "id": "file-c5a6e29a8ac648ab9f5162f6b010bb3c",
      "bytes": 10761,
      "created_at": 1735526413,
      "owner": "1",
      "filename": "法律常识.txt",
      "object": "file",
      "purpose": "kbs"
    },
    ...由于示例而省略部分内容...
    {
      "id": "file-b10fd265b9c445dfa0bd60b7eff151af",
      "bytes": 330880,
      "created_at": 1735480875,
      "owner": "1",
      "filename": "犯罪心理学.docx",
      "object": "file",
      "purpose": "kbs"
    }
  ],
  "object": "list"
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
GET 文件信息检索接口（Retrieve）
GET /files/{file_id}

返回有关特定文件的信息。
请求参数说明
名称	位置	类型	必选	说明
file_id	path	string	是	用于此请求的文件的 ID。
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ id	string	是	文件标识符。
+ object	string	是	对象类型：file
+ bytes	integer	是	文件的大小，以字节为单位。
+ created_at	integer	是	创建文件时的Unix时间戳（以秒为单位）。
+ filename	string	是	文件名称
+ purpose	string	是	文件的预期目的的文字简要说明。
+ owner	string	是	文件的所属用户ID。
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c \
  -H "Authorization: Bearer $API_KEY"
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
client.files.retrieve("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
1
2
3
请求体示例
无
响应体示例
复制
{
  "id": "file-c5a6e29a8ac648ab9f5162f6b010bb3c",
  "bytes": 10761,
  "created_at": 1735298816,
  "owner": "1",
  "filename": "法律常识.txt",
  "object": "file",
  "purpose": "kbs"
}
1
2
3
4
5
6
7
8
9
DELETE 文件删除接口（Delete）
DELETE /files/{file_id}

删除给定file_id的文件。
请求参数说明
名称	位置	类型	必选	说明
file_id	path	string	是	用于此请求的文件的 ID。
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ id	string	是	删除的文件标识
+ object	string	是	对象类型
+ deleted	boolean	是	是否删除成功
调用示例
代码示例
shell示例代码
复制
curl -s  -X DELETE ${BASE_URL}/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c \
  -H "Authorization: Bearer $API_KEY"
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
client.files.delete("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
1
2
3
请求体示例
无
响应体示例
复制
{
  "deleted": true,
  "id": "file-c5a6e29a8ac648ab9f5162f6b010bb3c",
  "object": "file"
}
1
2
3
4
5
GET 文件内容查找接口（Retrieve Content）
GET /files/{file_id}/content

返回有关特定文件的二进制内容
请求参数说明
名称	位置	类型	必选	说明
file_id	path	string	是	用于此请求的文件的 ID。
Authorization	header	string	是	授权码信息
响应参数说明
二进制数据
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c/content \
  -H "Authorization: Bearer $API_KEY" > 法律常识.txt
1
2
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
client.files.content("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
1
2
3
请求体示例
无
响应体示例
无
知识库（KnowledgeBase）管理
POST 知识库创建接口（Create）
POST /kbs

创建知识库并指定知识库中分块规则，重叠字数等内容
支持中文知识库名称。中文知识库在URL中，请采用URL编码
知识库创建/删除/分享后，平台内部会通知同步操作权限，对于后继知识库的操作有可能会出现短时间的无权限，时间在秒级。
知识库会创建在ES集群上，并采用bge-large-zh-v1.5向量模型进行向量化
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ name	body	string	是	知识库名称
+ description	body	string	是	知识库描述
+ split_config	body	object	否	
++ split_type	body	integer	否	分割算法
1：字数分割
++ chunk_max_len	body	integer	否	最大字数，取值在1-1000之内
++ chunk_overlap_len	body	integer	否	重叠字数，取值在0-1000之内
++ embedding_threshold	body	number	否	向量相似度阈值，取值在0.1-0.9之间，默认0.5
++ zh_title_enhance	body	boolean	否	是否开启中文标题加强
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	响应数据
++ id	string	是	知识库ID，创建后不可更改，可用于在URL中指定知识库
++ index_name	string	是	知识库在ES上映射的索引ID
++ name	string	是	知识库名称，创建时同id一致
++ description	string	是	知识库描述
++ created_at	string	是	知识库创建的时间戳
++ split_config	object	是	
+++ split_type	integer	是	分割算法
+++ chunk_max_len	integer	是	最大字数
+++ chunk_overlap_len	integer	是	重叠字数
+++ embedding_threshold	number	是	向量相似度阈值
+++ zh_title_enhance	body	boolean	否
++ owner	string	是	知识库所有者的用户ID
++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST ${BASE_URL}/kbs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "name": "法律知识库",
    "description": "法律知识库",
    "split_config": {
        "split_type": 1,
        "chunk_overlap_len": 50,
        "chunk_max_len": 512,
        "embedding_threshold": 0.5,
        "zh_title_enhance": true
    }
  }'
1
2
3
4
5
6
7
8
9
10
11
12
13
14
python示例代码
复制
import requests
import json
url = BASE_URL + "/kbs"
params = {
    "name": "法律知识库",
    "description": "法律知识库",
    "split_config": {
      "split_type": 1,
      "chunk_overlap_len": 50,
      "chunk_max_len": 512,
      "embedding_threshold": 0.5,
      "zh_title_enhance": true
    }
}
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json'
}
response = requests.post(url, data=json.dumps(params), headers=headers, verify=False)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
请求体示例
复制
{
  "name": "法律知识库",
  "description": "法律知识库",
  "split_config": {
    "split_type": 1,
    "chunk_overlap_len": 50,
    "chunk_max_len": 512,
    "embedding_threshold": 0.5,
    "zh_title_enhance": true
  }
}
1
2
3
4
5
6
7
8
9
10
11
响应体示例
复制
{
  "code": 200,
  "msg": "创建知识库成功",
  "data": [
    {
      "id": "法律知识库",
      "index_name": "vs_fa_lvzhi_shi_ku_1735613301",
      "name": "法律知识库",
      "description": "法律知识库",
      "created_at": 1735613301,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "embedding_threshold": 0.5,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1"
      ]
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
GET 知识库列表检索接口（List）
GET /kbs

知识库列表检索接口
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	响应数据
++ id	string	是	知识库ID
++ index_name	string	是	知识库在ES上映射的索引ID
++ name	string	是	知识库名称，创建时同id一致
++ description	string	是	知识库描述
++ created_at	string	是	知识库创建的时间戳
++ split_config	object	是	
+++ split_type	integer	是	分割算法
+++ chunk_max_len	integer	是	最大字数
+++ chunk_overlap_len	integer	是	重叠字数
+++ embedding_threshold	number	是	向量相似度阈值
+++ zh_title_enhance	boolean	否	是否开启中文标题加强
++ owner	string	是	知识库所有者的用户ID
++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/kbs \
  -H "Authorization: Bearer $API_KEY" 
1
2
python示例代码
复制
import requests

url = BASE_URL + "/kbs"
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json'
}

response = requests.get(url, headers=headers, verify=False)
1
2
3
4
5
6
7
8
9
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "查询知识库列表成功",
  "data": [
    {
      "id": "法律知识库",
      "index_name": "vs_fa_lvzhi_shi_ku_1735544372",
      "name": "法律知识库",
      "description": "法律知识库",
      "created_at": 1735544372,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1"
      ]
    },
    ...由于示例而省略部分内容...
    {
      "id": "案件知识库",
      "index_name": "vs_an_jianzhi_shi_ku_1735609869",
      "name": "案件知识库",
      "description": "案件知识库",
      "created_at": 1735609869,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1"
      ]
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
POST 知识库修改接口（Modify）
POST /kbs/{kbs_id}

修改知识库接口
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库ID
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ name	body	string	是	知识库名称
+ description	body	string	是	知识库描述
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	响应数据
++ id	string	是	知识库ID
++ index_name	string	是	知识库在ES上映射的索引ID
++ name	string	是	知识库名称，创建时同id一致
++ description	string	是	知识库描述
++ created_at	string	是	知识库创建的时间戳
++ split_config	object	是	
+++ split_type	integer	是	分割算法
+++ chunk_max_len	integer	是	最大字数
+++ chunk_overlap_len	integer	是	重叠字数
+++ zh_title_enhance	boolean	否	是否开启中文标题加强
++ owner	string	是	知识库所有者的用户ID
++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93  \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "name":"法律知识库-modify",
    "description":"法律知识库-modify"
    }'
1
2
3
4
5
6
7
Python示例代码
复制
from urllib.parse import quote
import requests
import json

url = BASE_URL + "/kbs/" + quote("法律知识库")
params = {
    "name": "法律知识库-modify",
    "description": "法律知识库-modify"
}
headers = {
    'Authorization': "Bearer " + API_KEY,
    'Content-Type': 'application/json'
}
response = requests.post(url, data=json.dumps(params), headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
请求体示例
复制
name: "法律知识库-modify"
description: "法律知识库-modify"
1
2
响应体示例
复制
{
  "code": 200,
  "msg": "修改知识库成功",
  "data": [
    {
      "id": "法律知识库",
      "index_name": "vs_fa_lvzhi_shi_ku_1735611103",
      "name": "法律知识库-modify",
      "description": "法律知识库-modify",
      "created_at": 1735611103,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1"
      ]
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
GET 知识库检索接口（Retrieve）
GET /kbs/{kbs_id}

知识库检索接口
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	响应数据
++ id	string	是	知识库ID
++ index_name	string	是	知识库在ES上映射的索引ID
++ name	string	是	知识库名称，创建时同id一致
++ description	string	是	知识库描述
++ created_at	string	是	知识库创建的时间戳
++ split_config	object	是	
+++ split_type	integer	是	分割算法
+++ chunk_max_len	integer	是	最大字数
+++ chunk_overlap_len	integer	是	重叠字数
+++ zh_title_enhance	boolean	否	是否开启中文标题加强
++ owner	string	是	知识库所有者的用户ID
++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93 \
  -H "Authorization: Bearer $API_KEY" 
1
2
Python示例代码
复制
from urllib.parse import quote
import json

url = BASE_URL + "/kbs/" + quote("法律知识库")
headers = {
    'Authorization': "Bearer " + API_KEY,
    'Content-Type': 'application/json'
}
response = requests.get(url, headers=headers)
1
2
3
4
5
6
7
8
9
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "查询指定知识库信息成功",
  "data": [
    {
      "id": "法律知识库",
      "index_name": "vs_fa_lvzhi_shi_ku_1735611482",
      "name": "法律知识库",
      "description": "法律知识库",
      "created_at": 1735611482,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1"
      ]
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
DELETE 知识库删除接口（Delete）
DELETE /kbs/{kbs_id}

知识库删除接口
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
调用示例
代码示例
shell示例代码
复制
curl -s  -X DELETE ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" 
1
2
3
Python示例代码
复制
from urllib.parse import quote
import requests

url = BASE_URL + "/kbs/" + quote("法律知识库")
headers = {
    'Authorization': "Bearer " + API_KEY,
    'Content-Type': 'application/json'
}
response = requests.delete(url, headers=headers)
1
2
3
4
5
6
7
8
9
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "知识库删除成功"
}
1
2
3
4
POST 知识库分享接口（Share）
POST /kbs/{kbs_id}/share

将当前用户创建的知识库分享给指定用户
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ user_ids	body	[string]	否	待分享的用户id集合
+ action	body	string	否	SHARE/UNSHARE, 分享/不分享
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	响应数据
++ id	string	是	知识库ID
++ index_name	string	是	知识库在ES上映射的索引ID
++ name	string	是	知识库名称，创建时同id一致
++ description	string	是	知识库描述
++ created_at	string	是	知识库创建的时间戳
++ split_config	object	是	
+++ split_type	integer	是	分割算法
+++ chunk_max_len	integer	是	最大字数
+++ chunk_overlap_len	integer	是	重叠字数
+++ zh_title_enhance	boolean	否	是否开启中文标题加强
++ owner	string	是	知识库所有者的用户ID
++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/share \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"user_ids": ["2"]}'
1
2
3
4
Python示例代码
复制
import requests
import json

url = BASE_URL + "/kbs/" + quote("法律知识库") + "/share"
params = {"user_ids": ['2']}
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json'
}
response = requests.post(url, data=json.dumps(params), headers=headers)
1
2
3
4
5
6
7
8
9
10
请求体示例
复制
{
  "user_ids": [
    "2"
  ]
}
1
2
3
4
5
响应体示例
复制
{
  "code": 200,
  "msg": "知识库分享动作成功",
  "data": [
    {
      "id": "法律知识库",
      "index_name": "vs_fa_lvzhi_shi_ku_1735614490",
      "name": "法律知识库-modify",
      "description": "法律知识库-modify",
      "created_at": 1735614490,
      "split_config": {
        "split_type": 1,
        "chunk_max_len": 512,
        "chunk_overlap_len": 50,
        "zh_title_enhance": true
      },
      "owner": "1",
      "user_ids": [
        "1",
        "2"
      ]
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
POST 知识库重置接口（Reparsing）
POST /kbs/{kbs_id}/reparsing

根据知识库id将知识库进行重新解析
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
++ split_type	body	integer	否	分割算法
1：字数分割
++ chunk_max_len	body	integer	否	最大字数，取值在1-1000之内
++ chunk_overlap_len	body	integer	否	重叠字数，取值在0-1000之内
++ zh_title_enhance	boolean	否	是否开启中文标题加强	
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/reparsing \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
        "split_type": 1,
        "chunk_overlap_len": 0,
        "chunk_max_len": 600,
        "zh_title_enhance": true
      }'
1
2
3
4
5
6
7
8
9
Python示例代码
复制
import requests
import json

url = BASE_URL + "/kbs/" + quote("法律知识库") + "/reparsing"
params = {
    'type': 1,
    'chunk_max_len': 600,
    'chunk_overlap_len': 0
}
headers = {
    'Authorization': "Bearer " + API_KEY,
    'Content-Type': 'application/json'  
}
response = requests.post(url, data=json.dumps(params), headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
请求体示例
复制
{
  "type": 1,
  "chunk_max_len": 600,
  "chunk_overlap_len": 0
}
1
2
3
4
5
响应体示例
复制
{
  "code": 200,
  "msg": "知识库重置成功"
}
1
2
3
4
知识库关联（Association）管理
POST 知识库文件创建接口（Add Files）
POST /kbs/{kbs_id}/files

功能：将文件和知识库进行关联
知识库文件关联，当前版本未提供进度查询，在轻负载的情况下，可以使用2万字/分钟进行估算
现支持的知识库关联的文件格式如下：txt、pdf、json、epub、docx、xls、xlsx、csv、xml、md多种格式，建议采用txt格式
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ file_ids	body	[string]	是	文件id列表
响应参数说明
调用/回调响应
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	否	响应信息
+ data	[object]	是	响应数据
++ task_id	string	是	任务ID
++ kbs_id	string	是	知识库ID
++ files	[object]	否	文件处理结果
+++ code	integer	是	此文件的文件ID的处理响应码
+++ file_id	string	是	文件id
+++ file_name	string	是	文件名称
+++ file_msg	string	是	文件处理结果
++ start_time	string	否	任务开始时间
++ end_time	string	否	任务结束时间
++ cost	integer	否	任务消耗时间
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/files \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
          "file_ids": ["file-c5a6e29a8ac648ab9f5162f6b010bb3c"],
          "callback": "http://${YOUR_CALLBACK_HOST}:${YOUR_CALLBACK_PORT}/callback"
      }'
1
2
3
4
5
6
7
Python示例代码
复制
from urllib.parse import quote
import requests
import json

#绑定文件到知识库
url = BASE_URL +"/kbs/" + quote("法律知识库") + "/files"
params = {
    'file_ids' : [ "file-c5a6e29a8ac648ab9f5162f6b010bb3c" ],
    #使用自己的测试回调方法
    'callback' : f"http://{YOUR_CALLBACK_HOST}:{YOUR_CALLBACK_PORT}/callback"  
}
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json'
}
response = requests.post(url, data=json.dumps(params), headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
请求体示例
复制
{
  "file_ids": ["file-c5a6e29a8ac648ab9f5162f6b010bb3c"],
  "callback": "http://${YOUR_CALLBACK_HOST}:${YOUR_CALLBACK_PORT}/callback"
}
1
2
3
4
响应体示例
调用响应
复制
{
  "code": 202,
  "msg": "任务已接受",
  "data": [
    {
      "start_time": "2024-12-31 07:52:02",
      "callback": "http://202.127.0.242:19195/v2/kbs/test/callback",
      "task_id": "251a55e0-9ea3-42d0-85ea-46841c2747f8",
      "kbs_id": "法律知识库"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
回调响应
复制
{
  "code": 200,
  "msg": "文件关联知识库成功",
  "data": [
    {
      "start_time": "2024-12-31 06:48:36",
      "cost": 29,
      "end_time": "2024-12-31 06:49:05",
      "files": [
        {
          "code": 200,
          "file_msg": "成功加载文件进知识库",
          "file_name": "法律常识.txt",
          "file_id": "file-97fbbe46b4514e9f9e2141b7cadf69b7"
        }
      ],
      "task_id": "26c5bf46-81bb-4b45-b538-9f0c9b8b2b9d",
      "kbs_id": "法律知识库"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
GET 知识库文件列表检索接口（List Files）
GET /kbs/{kbs_id}/files

获取指定知识库下的所有文件
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	知识库文件对象集合
++ id	string	是	文件标识符。
++ object	string	是	对象类型：file
++ bytes	integer	是	文件的大小，以字节为单位。
++ created_at	integer	是	创建文件时的Unix时间戳（以秒为单位）。
++ owner	string	是	文件属主的ID
++ filename	string	是	文件名称
++ purpose	string	是	文件的预期目的的文字简要说明。
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/files \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"
1
2
3
Python示例代码
复制
import requests
from urllib.parse import quote

url = BASE_URL +"/kbs/" + quote("法律知识库") + "/files"
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json' 
}
response = requests.get(url, headers=headers)
1
2
3
4
5
6
7
8
9
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "知识库文件列表检索成功",
  "data": [
    {
      "id": "file-c5a6e29a8ac648ab9f5162f6b010bb3c",
      "bytes": 10761,
      "created_at": 1731052018,
      "owner": "1",
      "filename": "法律常识.txt",
      "object": "file",
      "purpose": "kbs"
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
GET 知识库文件检索接口（Retrieve Files）
GET /kbs/{kbsid}/files/{fileid}

知识库文件检索接口，同时检索文件和知识库元数据
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
kbs_id	path	string	是	知识库标识
file_id	path	string	是	文件标识
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
+ data	[object]	是	知识库文件对象集合
++ file	object	是	文件对象，文件与知识库已未关联时不返回
+++ id	string	是	文件标识符。
+++ object	string	是	对象类型：file
+++ bytes	integer	是	文件的大小，以字节为单位。
+++ created_at	integer	是	创建文件时的Unix时间戳（以秒为单位）。
+++ owner	string	是	文件属主的ID
+++ filename	string	是	文件名称
+++ purpose	string	是	文件的预期目的的文字简要说明。
++ knowledgeBase	object	是	知识库对象
+++ id	string	是	知识库ID，创建后不可更改，可用于在URL中指定知识库
+++ index_name	string	是	知识库在ES上映射的索引ID
+++ name	string	是	知识库名称，创建时同id一致
+++ description	string	是	知识库描述
+++ created_at	string	是	知识库创建的时间戳
+++ split_config	object	是	
++++ split_type	integer	是	分割算法
++++ chunk_max_len	integer	是	最大字数
++++ chunk_overlap_len	integer	是	重叠字数
++++ zh_title_enhance	boolean	是	是否开启中文标题加强
+++ owner	string	是	知识库所有者的用户ID
+++ user_ids	[string]	是	可以访问知识库的用户ID
调用示例
代码示例
shell示例代码
复制
curl -s  -X GET ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"
1
2
3
Python示例代码
复制
from urllib.parse import quote
import requests

url = BASE_URL +"/kbs/" + quote("法律知识库") + "/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c"
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json' 
}
response = requests.get(url, headers=headers)
1
2
3
4
5
6
7
8
9
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "知识库检索文件成功",
  "data": [
    {
      "file": {
        "id": "file-a4f7d1959fcd45aabcd9935f6e0612cc",
        "bytes": 10761,
        "created_at": 1735904592,
        "owner": "1",
        "filename": "法律常识.txt",
        "object": "file",
        "purpose": "kbs"
      },
      "knowledgeBase": {
        "id": "法律知识库",
        "index_name": "vs_fa_lvzhi_shi_ku_1735904594",
        "name": "法律知识库",
        "description": "法律知识库",
        "created_at": 1735904594,
        "split_config": {
          "split_type": 1,
          "chunk_max_len": 512,
          "chunk_overlap_len": 50,
          "zh_title_enhance": true
        },
        "owner": "1",
        "user_ids": [
          "1"
        ]
      }
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
DELETE 知识库文件删除接口（Remove Files）
DELETE /kbs/{kbsid}/files/{fileid}

删除知识库里相应的文件
请求参数说明
名称	位置	类型	必选	说明
kbs_id	path	string	是	知识库标识
file_id	path	string	是	文件标识
Authorization	header	string	是	授权码信息
响应参数说明
名称	类型	必填	说明
body			响应体
+ code	integer	是	响应码
+ msg	string	是	响应信息
调用示例
代码示例
shell示例代码
复制
curl -s  -X DELETE ${BASE_URL}/kbs/%E6%B3%95%E5%BE%8B%E7%9F%A5%E8%AF%86%E5%BA%93/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c \
  -H "Authorization: Bearer $API_KEY"
1
2
Python示例代码
复制
from urllib.parse import quote
import requests

url = BASE_URL + "/kbs/" + quote("法律知识库") + "/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c"
headers = {
    'Authorization': "Bearer " + API_KEY
}
response = requests.delete(url, headers=headers)
1
2
3
4
5
6
7
8
请求体示例
无
响应体示例
复制
{
  "code": 200,
  "msg": "删除文件关联成功，已清除知识库中的文件数据。"
}
1
2
3
4
向量（Embeddings）接口
POST 向量创建（Create）
POST /embeddings

获取给定输入的矢量表示，创建表示输入文本的嵌入向量。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ model	body	string	是	要使用的模型的 ID
+ input	body	string/[string]	是	输入文本,长度不得超过1024
+ encoding_format	body	string	否	返回嵌入的格式:float
+ dimensions	body	integer	否	生成的输出维度数量:1024
响应参数说明
名称	类型	必填	说明
body			响应体
+ object	string	是	对象类型
+ model	string	是	要使用的模型的ID
+ data	[object]	是	
++ object	string	否	对象类型
++ embedding	[float]	否	嵌入向量，这是一个浮点数列表
++ index	integer	否	嵌入列表中的嵌入索引
+ usage	object	是	令牌使用统计
++ prompt_tokens	integer	是	提示符中的令牌数量。
++ completion_tokens	integer	是	生成完成中的令牌数量。
++ total_tokens	integer	是	请求中使用的令牌总数（提示+完成）。
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/embeddings \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "法律文件的测试文本",
    "model": "ayenaembedding-001",
    "dimensions": 1024,
    "encoding_format": "float"
  }'
1
2
3
4
5
6
7
8
9
python示例代码
复制
import openai

contents = "法律文件的测试文本"
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
params = {
    'model' : "ayenaembedding-001",
    'input' : contents,
    'dimensions' : 1024,
    'encoding_format': "float"
}
response = client.embeddings.create(**params)
1
2
3
4
5
6
7
8
9
10
11
请求体示例
复制
{
  "input": "测试文本",
  "model": "ayenaembedding-001",
  "dimensions": 1024,
  "encoding_format": "float"
}
1
2
3
4
5
6
响应体示例
复制
{
  "data": [
    {
      "embedding": [
        0.027686400339007378,
        -0.021410861983895302,
        ...由于示例而省略部分内容...,
        -0.0025556262116879225,
        -0.009135007858276367
      ],
      "index": 0,
      "object": "embedding"
    }
  ],
  "model": "ayenaembedding-001",
  "object": "list",
  "usage": {
    "total_tokens": 5
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
重排序（Rerank）接口
POST 重排序（rerank）
POST /rerank

对搜索结果进行重排序。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body				请求体
+ model	body	string	是	要使用的模型的 ID
+ query	body	string	是	输入文本,长度不得超过1024
+ documents	body	string	是	待排序的搜索结果
+ top_k	body	integer	否	返回的搜索结果数,默认返回所有结果
响应参数说明
名称	类型	必填	说明
body			响应体
+ results	[result]	是	对象类型
++ index	integer	是	结果位于搜索结果中的索引
++ relevance_score	float	是	评分结果,结果输出顺序按照评分结果由大到小输出
+ id	string	是	请求唯一ID
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/rerank \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-reranker-base",
    "query": "什么是人工智能",
    "documents": ["AI是机器学习的分支", "人工智能是计算机科学领域", "窗前明月光,疑是地上霜", "c++是最好的编程语言"],
    "top_k": 3
  }'
1
2
3
4
5
6
7
8
9
dify示例配置
复制
模型类型: Rerank
模型名称: bge-rerank-base
API-Key: 输入您的锐智key
API endpoint URL: http://*.*.*.*:*/v1
1
2
3
4
python示例代码
复制
import requests
url = URL
key = KEY
data = {
            "model": "bge-reranker-base",
            "query": "什么是人工智能？",
            "documents": ["AI是机器学习的分支", "人工智能是计算机科学领域", "窗前明月光,满地大石头", "c++是最好的编程语言"],
            "top_k": 3
        }
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {key}"
}
response = requests.post(url, json=data, headers=headers)
print(response.json())
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
请求体示例
复制
{
  "model": "bge-reranker-base",
  "query": "什么是人工智能？",
  "documents": ["AI是机器学习的分支", "人工智能是计算机科学领域", "窗前明月光,满地大石头", "c++是最好的编程语言"],
  "top_k": 3
}
1
2
3
4
5
6
响应体示例
复制
{
  "results":[
    {"index":1,"relevance_score":6.747413635253906},
    {"index":0,"relevance_score":6.239818572998047},
    {"index":3,"relevance_score":-4.944884777069092}
  ],
  "id":"rerank-94f6c76aac22415db93bfd95ac929fba"
}
1
2
3
4
5
6
7
8
音频（Audio）接口
POST 音频生成（Create）
POST /audio/speech

通过传入的参数创建指定的语音对象
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	application/json
body		object		请求体
+ model	body	string	是	可用的音频模型
+ input	body	string	是	要生成音频的文本，最长不得超过1024字符
+ voice	body	string	否	语音类型参数(voice,目前支持两种:male/female.分别对应男女声)
+ response_format	body	string	否	目前支持wav音频的格式
+ speed	body	number	否	生成的音频速度。选择0.1到4.0之间的值。
响应参数说明
生成的音频数据流
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/audio/speech \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ayenaaudio-001",
    "response_format": "wav",
    "input": "您好，我是云网AI服务平台，请问有什么可以帮助您！",
    "voice": "female",
    "speed": 1.0
  }' \
  --output out/TestAudioSpeechPost.wav
1
2
3
4
5
6
7
8
9
10
11
python示例代码
复制
from pathlib import Path
import openai

client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
speech_file_path = f'out/TestAudioSpeechPost.wav'
params = {
    "model": "ayenaaudio-001",
    "response_format": "wav",
    "input": f"您好，我是云网AI服务平台，请问有什么可以帮助您！",
    "voice": "female",
    "speed": 1.0
}
response = client.audio.speech.create(**params)
1
2
3
4
5
6
7
8
9
10
11
12
13
请求体示例
复制
{
  "model": "ayenaaudio-001",
  "response_format": "wav",
  "input": "您好，我是云网AI服务平台，请问有什么可以帮助您！",
  "voice": "female",
  "speed": 1.0
}
1
2
3
4
5
6
7
响应体示例
输出音频二进制流
POST 音频转录（Transcriptions）
POST /audio/transcriptions

将音频转换为文本
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	multipart/form-data
body				请求体
+ file	body	file	是	要转录的音频文件对象,格式:wav
+ model	body	string	是	要使用的模型ID
+ language	body	string	否	输入音频的语言：zh,en
+ prompt	body	string	-	暂不支持
+ response_format	body	string	-	转录输出的格式，暂不支持
+ temperature	body	number	-	采样温度， 暂不支持
响应参数说明
名称	类型	必填	说明
body			响应体
+ text	string	是	转录后的文本内容
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/audio/transcriptions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@resource/zh.wav" \
  -F language="zh" \
  -F model="ayenaaudio-001"
1
2
3
4
5
6
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)

params = {
    "model": "ayenaaudio-001",
    "language": "zh",
    "file" : open("resource/zh.wav", "rb")
}
response = client.audio.transcriptions.create(**params)
1
2
3
4
5
6
7
8
9
请求体示例
复制
file: speech.wav
model: ayenaaudio-001
language: zh
1
2
3
响应体示例
复制
{
  "text": "我认为跑步最重要的就是给我带来了身体健康"
}
1
2
3
WS 实时音频转录（ASR）
ws /audio/speech/asr

语音转文本实时接口
鉴权
client 建立连接时，在请求头中加入ApiKey
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
开始信号
client 通过开始信号传入流式识别音频信息
字段	必选	类型	说明
command	是	string	流式识别中命令类型
hotword	否	string	热词
请求示例
复制
{"command": "start", "hotword": "北京 天安门"}
1
server 信息 server 端返回新连接的情况
字段	必选	类型	说明
status	是	string	ASR服务端状态
signal	是	string	该流式连接必要的准备工作是完成状态
复制
 {"signal": "server_ready", "status": "ok"}
1
数据
client和server建立连接之后，client端不断地向服务端发送数据

client 信息 发送 单声道/16k采样/16bit/PCM 数据流到服务端
server 信息 每发送一个数据，服务端会将该数据包解码的结果返回出来
字段	必选	类型	说明
result	是	string	ASR解码的结果
结束
client 发送完最后最后一个数据包之后，需要发送给服务端一个结束的命令，通知服务端销毁该链接的相关资源。 通过开始信号传入流式识别音频信息，以及解码参数

字段	必选	类型	说明
command	是	string	流式识别中命令类型
请求示例
复制
{"command": "end"}
1
server 信息 server 端返回新连接的情况
字段	必选	类型	说明
status	是	string	ASR服务端状态
signal	是	string	该流式连接必要的准备工作是完成状态
result	是	string	ASR最后解码的结果
复制
 {"signal": "finished", "status": "ok", "result": "你好我是Ayena"}
1
调用示例
python示例代码
复制
import asyncio
import ssl

import websockets
import wave
import json

async def send_audio(file_path, auth_token):
    uri = "wss://${BASE_URL}/audio/speech/asr"  # 更改为你的实际服务地址

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE


    headers = {
        'Authorization': f'Bearer {auth_token}'
    }

    async with websockets.connect(uri, ssl=ssl_context, extra_headers=headers) as websocket:
        try:
            start_signal = {"command": "start"}
            await websocket.send(json.dumps(start_signal))

            # 读取音频文件并分块发送
            with wave.open(file_path, 'rb') as wf:
                chunk_size = 9600  # 与服务端的一致
                data = wf.readframes(chunk_size)
                while data:
                    await websocket.send(data)
                    data = wf.readframes(chunk_size)

            # 发送 "end" 信号
            end_signal = {"command": "end"}
            await websocket.send(json.dumps(end_signal))

            # 接收结果
            async for message in websocket:
                print(f"Received message: {message.encode('utf-8').decode('unicode_escape')}")
                try:
                    response = json.loads(message)
                    if response.get("signal") == "finished":
                        print(f"ASR Result: {response.get('result')}")
                        break
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {str(e)}")
        finally:
            await websocket.close()

# 运行事件循环
asyncio.run(send_audio('output.wav', 'sk-36dc94XXXXXXXXXXXXXXXXXXXXXXXX'))
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
python调用返回结果示例
复制
Received message: {"signal": "server_ready", "status": "ok"}
Received message: {"result": "你好"}
Received message: {"result": "你好"}
Received message: {"result": "你好，小静。", "signal": "finished", "status": "ok"}
ASR Result: 你好，小静。
1
2
3
4
5
POST 音频翻译（Translations）
POST /audio/translations

将音频翻译成中文
目前主要支持英文语音翻译
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
body				请求体
+ file	body	string(binary)	是	要转录的音频文件对象,格式为:wav等。
+ model	body	string	是	要使用的模型 ID
+ language	body	string	-	暂不支持，仅支持英转中
+ prompt	body	string	-	暂不支持
+ response_format	body	string	-	转录输出的格式, 暂不支持
+ temperature	body	number	-	采样温度, 暂不支持
响应参数说明
名称	类型	必填	说明
body			响应体
+ text	string	是	翻译后的文本内容
调用示例
代码示例
shell示例代码
复制
curl -s  ${BASE_URL}/audio/translations \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F file="@speech.wav" \
  -F model="ayenaaudio-001"
1
2
3
4
5
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)

params = {
    "model": "ayenaaudio-001",
    "file" : open("resource/en.wav", "rb")
}
response = client.audio.translations.create(**params)
1
2
3
4
5
6
7
8
请求体示例
复制
file: speech.wav
model: ayenaspring-pro-001
1
2
响应体示例
复制
{
  "text": "有什么新闻，请念一下。"
}
1
2
3
工具（Tools）接口
POST 文本翻译接口（Translations）
POST /tools/translations

文本翻译API是一种高效、准确的翻译工具，能够将文本内容快速翻译成多种语言，满足不同领域和场景的翻译需求。可用于：

自动识别输入语言文字，翻译成其他语种文本
根据不同场景，翻译成指定语种文本
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
body				请求体
+ model	body	string	是	模型名称
+ content	body	string	是	待翻译的文本
+ src_lang	body	string	否	源文本语种(取值参考"语言编码"，置空，则自动检测语种)
+ dst_lang	body	string	否	目标文本语种(取值参考"语言编码"，置空，则默认为中文)
+ situation	body	string	否	场景(外交，新闻等，描述不超过10个字符)
响应参数说明
名称	类型	必填	说明
+ code	integer	是	响应编码
+ data	list	是	翻译后的文本内容
调用示例
shell示例代码
复制
curl -s  ${BASE_URL}/tools/translations \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"ayenaspring-pro-001",
    "content":"我能为您提供精准的引导式解答，并在必要时引用实例作为参考",
    "dst_lang":"en"
    }' 
1
2
3
4
5
6
7
8
python示例代码
复制
url = f"{BASE_URL}/tools/translations"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
data = {
    "model": "ayenaspring-pro-001",
    "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考",
    "dst_lang": "en"
}

response = requests.post(url, headers=headers, data=json.dumps(data))
1
2
3
4
5
6
7
8
9
10
11
12
请求示例
复制
{
    "model": "ayenaspring-pro-001",
    "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考",
    "dst_lang": "en"
}
1
2
3
4
5
响应示例
响应示例
复制
{
  "code": 200,
  "data": [
    "I can provide you with precise, guided answers, and refer to examples as needed."
  ]
}
1
2
3
4
5
6
POST Token核算接口（Tokens）
POST /tools/tokens

对相应的输入进行分解，按系统当前的算法提供token拆分的数量。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
body				请求体
+ model	body	string	是	模型名称
+ content	body	string	是	待进行token分解的内容
响应参数说明
名称	类型	必填	说明
+ tokens	integer	是	分解后token的数量
调用示例
shell示例代码
复制
curl -s  ${BASE_URL}/tools/tokens \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ayenaspring-pro-001",
    "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考"
    }' 
1
2
3
4
5
6
7
python示例代码
复制
import requests
import json

url = BASE_URL + "/tools/tokens"
params = {
    "model": "ayenaspring-pro-001",
    "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考"
}
headers = {
    'Authorization': "Bearer "+API_KEY,
    'Content-Type': 'application/json'
}
response = requests.post(url, data=json.dumps(params), headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
请求示例
复制
{
"model": "ayenaspring-pro-001",
"content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考"
}
1
2
3
4
响应示例
响应示例
复制
{
  "tokens": 19
}
1
2
3
POST OCR识别接口（Paddle）
POST /tools/ocr/paddle

通过Paddle ocr进行OCR识别，支持多种参数配置。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	multipart/form-data
body				请求体
+ image	body	file	是	要进行OCR识别的图像文件
+ useanglecls	body	boolean	否	是否使用角度分类，默认 true
+ lang	body	string	否	语言代码，默认 "ch"（中文）
+ detdbthresh	body	number	否	检测阈值，默认 0.3
+ detdbbox_thresh	body	number	否	检测框阈值，默认 0.5
+ detdbunclip_ratio	body	number	否	检测框扩展比例，默认 1.6
响应参数说明
名称	类型	必填	说明
+ success	boolean	是	识别是否成功
+ results	array	是	识别结果数组
++ text	string	是	识别出的文本内容
++ confidence	number	是	置信度
++ bbox	array	是	边界框坐标[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
+ processing_time	number	是	处理时间（秒）
+ image_size	object	是	图像尺寸信息
++ width	integer	是	图像宽度
++ height	integer	是	图像高度
调用示例
shell示例代码
复制
curl -s  ${BASE_URL}/tools/ocr/paddle \
  -H "Authorization: Bearer $API_KEY" \
  -F image=@screenshot.png \
  -F use_angle_cls=true \
  -F lang="ch" \
  -F det_db_thresh=0.3 \
  -F det_db_box_thresh=0.5 \
  -F det_db_unclip_ratio=1.6
1
2
3
4
5
6
7
8
python示例代码
复制
import requests
import json

url = BASE_URL + "/tools/ocr/paddle"
files = {
    "image": open("screenshot.png", "rb")
}
data = {
    "use_angle_cls": True,
    "lang": "ch",
    "det_db_thresh": 0.3,
    "det_db_box_thresh": 0.5,
    "det_db_unclip_ratio": 1.6
}
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.post(url, files=files, data=data, headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
请求示例
复制
{
  "image": "screenshot.png",
  "use_angle_cls": true,
  "lang": "ch",
  "det_db_thresh": 0.3,
  "det_db_box_thresh": 0.5,
  "det_db_unclip_ratio": 1.6
}
1
2
3
4
5
6
7
8
响应示例
响应示例
复制
{
  "success": true,
  "results": [
    {
      "text": "1月份工作。",
      "confidence": 0.9218947887420654,
      "bbox": [
        [
          553,
          83
        ],
        [
          646,
          83
        ],
        [
          646,
          110
        ],
        [
          553,
          110
        ]
      ]
    },
    {
      "text": "txt",
      "confidence": 0.9969037373860677,
      "bbox": [
        [
          584,
          109
        ],
        [
          616,
          109
        ],
        [
          616,
          133
        ],
        [
          584,
          133
        ]
      ]
    },
    {
      "text": "bzt目前问题.",
      "confidence": 0.9432640895247459,
      "bbox": [
        [
          544,
          232
        ],
        [
          653,
          232
        ],
        [
          653,
          255
        ],
        [
          544,
          255
        ]
      ]
    },
    {
      "text": "截图工具",
      "confidence": 0.999423086643219,
      "bbox": [
        [
          177,
          263
        ],
        [
          256,
          263
        ],
        [
          256,
          287
        ],
        [
          177,
          287
        ]
      ]
    }
  ],
  "processing_time": 0.1565,
  "image_size": {
    "width": 1196,
    "height": 800
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
POST OCR识别接口（DeepSeek）
POST /tools/ocr/deepseek

通过DeepSeek模型进行OCR识别，支持多种任务类型和分辨率设置。
请求参数说明
名称	位置	类型	必选	说明
Authorization	header	string	是	授权码信息
Content-Type	header	string	是	multipart/form-data
body				请求体
+ image	body	file	是	要进行OCR识别的图像文件
+ task_type	body	string	否	任务类型，枚举值：freeocr, markdown, parsechart, locate_object，默认为markdown
+ resolution	body	string	否	分辨率，枚举值：tiny, small, base, large, gundam，默认为gundam
响应参数说明
名称	类型	必填	说明
+ success	boolean	是	识别是否成功
+ results	array	是	识别结果数组
++ label	string/null	否	标签
++ text	string	是	识别出的文本内容
++ confidence	number	是	置信度
++ bbox	array	是	边界框坐标[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
+ processing_time	number	是	处理时间（秒）
+ image_size	object	是	图像尺寸信息
++ width	integer	是	图像宽度
++ height	integer	是	图像高度
+ text	string/null	否	识别的文本
+ processed_text	string/null	否	处理后的文本
调用示例
shell示例代码
复制
curl -s  ${BASE_URL}/tools/ocr/deepseek \
  -H "Authorization: Bearer $API_KEY" \
  -F image=@screenshot.png \
  -F task_type="free_ocr" \
  -F resolution="base"
1
2
3
4
5
python示例代码
复制
import requests
import json

url = BASE_URL + "/tools/ocr/deepseek"
files = {
    "image": open("screenshot.png", "rb")
}
data = {
    "task_type": "free_ocr",
    "resolution": "base"
}
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.post(url, files=files, data=data, headers=headers)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
请求示例
复制
{
  "image": "screenshot.png",
  "task_type": "free_ocr",
  "resolution": "base"
}
1
2
3
4
5
响应示例
响应示例
复制
{
  "success": true,
  "results": [
    {
      "label": "image",
      "text": "image",
      "confidence": 1.0,
      "bbox": [
        [
          562,
          5
        ],
        [
          634,
          5
        ],
        [
          634,
          79
        ],
        [
          562,
          79
        ]
      ]
    },
    {
      "label": "text",
      "text": "1月份工作。",
      "confidence": 1.0,
      "bbox": [
        [
          550,
          81
        ],
        [
          647,
          81
        ],
        [
          647,
          104
        ],
        [
          550,
          104
        ]
      ]
    }
  ],
  "processing_time": 4.5648,
  "image_size": {
    "width": 1196,
    "height": 800
  },
  "text": "<|ref|>image<|/ref|><|det|>[[470, 7, 530, 99]]<|/det|>\n \n\n<|ref|>text<|/ref|><|det|>[[460, 102, 541, 130]]<|/det|>\n1月份工作。 ",
  "processed_text": "![](images/0.jpg)\n\n \n\n\n1月份工作。 "
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
会话（Chat）接口
POST 会话接口（ChatCompletions）
POST /chat/completions

支持与用户进行对话，具体会话模型限制请参见Model列表检索
支持流式会话，会以HTTP流式输出用户会话内容。
支持在run角色里用@{知识库ID}的方式，进行知识库的会话。以最后一个run角色内容为准。
支持同时进行多个有权限的知识库进行会话。
知识库会话时，请注意预留一些Token空间，以免历史数据引入和系统添加的提示词时超过模型承受范围。
函数调用，上下文长度等模型固有参数，请参考文档"参数数据：模型参数"
请求参数说明
名称	位置	类型	必选	说明
Content-Type	header	string	是	application/json
Authorization	header	string	是	授权码信息
body				请求体
+ model	body	string	是	要使用的模型的 ID
+ messages	body	[object]	是	至今为止对话所包含的消息列表
++ role	messages	string	是	发起聊天内容的角色，取值user、system、assistant。
++ content	messages	string	是	发起的聊天内容，暂不支持数组
++ name	messages	string	否	发起的聊天的用户，区分不同用户
+ temperature	body	integer	否	采样温度，介于 0 和 2 之间。建议<1.6，过大的温度生成的文档会无法阅读
+ top_p	body	integer	否	核采样，其中模型考虑具有 top_p 概率质量的标记的结果。所以 0.1 意味着只考虑构成前 10% 概率质量的标记
+ n	body	integer	-	为每个输入消息生成多少个聊天补全选择。暂不支持
+ stream	body	boolean	否	默认为 false，为true 时，会以HTTP流式输出用户会话内容
+ stop	body	string	否	默认为 null, 大模型在"停止文本"出现时，会中断内容生成
+ max_tokens	body	integer	否	在会话中能够输出的最大量，为空时为本模型的最大输出量。会话在超出此量时会中断内容生成。此值因具体模型不同也不同。可通过接口查询模型具体信息
+ presence_penalty	body	float	否	-2.0 和 2.0 之间的数字。正值会根据到目前为止是否出现在文本中来惩罚新标记，从而增加模型谈论新主题的可能性
+ frequency_penalty	body	float	否	默认为 0。-2.0 到 2.0 之间的数字。负值会鼓励重复，建议使用>=0的正值
+ logit_bias	body	null	-	修改指定标记出现在补全中的可能性。暂不支持
+ user	body	string	-	代表您的最终用户的唯一标识符。暂不支持
+ response_format	body	object	-	指定模型必须输出的格式的对象。 暂不支持
+ seen	body	integer	-	暂不支持
+ tools	body	[object]	是	模型可以调用的一组工具列表。目前,只支持作为工具的函数。使用此功能来提供模型可以为之生成 JSON 输入的函数列表。(当前仅支持非流式请求下的调用，即stream=false时)
++ type	tools	string	是	工具的类型
++ function	tools	object	是	功能对象
+++ name	function	string	否	要调用的函数的名称。必须是a-z，A-Z，0-9，或包含下划线和破折号，最大长度为64
+++ description	function	string	否	描述该函数的作用，由模型用于选择何时以及如何调用该函数
+++ parameters	function	object	否	函数接受的参数，描述为JSON Schema对象。有关示例，请参阅指南，以及有关格式的文档的JSON模式参考
+ tool_choice	body	object	是	控制模型调用哪个函数(如果有的话)。none 表示模型不会调用函数,而是生成消息。auto 表示模型可以在生成消息和调用函数之间进行选择
响应参数说明
名称	类型	必填	说明
body			响应体
+ id	string	是	聊天的唯一标识符
+ object	string	是	对象类型：chat.completion/chat.completion.chunk
+ model	string	是	聊天使用的模型
+ created	integer	是	创建聊天完成时的Unix时间戳（以秒为单位）
+ choices	[object]	是	聊天结果的选项列表
++ index	integer	否	选择列表中的选择索引
++ message	object	否	
+++ role	string	是	这条消息的作者的角色
+++ content	string	是	消息的内容
+++ tool_calls	[object]	否	模型生成的工具调用，例如函数调用
++++ id	string	是	工具调用的 ID
++++ type	string	是	工具的类型: function
++++ function	object	是	模型调用的函数
+++++ name	string	是	要调用的函数的名称
+++++ arguments	string	是	用于调用函数的参数，由模型以 JSON 格式生成。请注意，该模型并不总是生成有效的 JSON，并且可能会产生函数架构未定义的参数。在调用函数之前验证代码中的参数
++ finish_reason	string	否	模型停止生成令牌的原因
+ usage	object	是	完成请求的使用统计信息
++ prompt_tokens	integer	是	提示符中的令牌数量
++ completion_tokens	integer	是	生成完成中的令牌数量
++ total_tokens	integer	是	请求中使用的令牌总数（提示+完成）
调用示例（非流式）
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"\
  -d '{
    "messages": [
        {
            "content": "公安执法办案的流程有哪些？",
            "role": "user"
        }
    ],
    "model": "ayenaspring-pro-001"
  }'
1
2
3
4
5
6
7
8
9
10
11
12
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY,base_url=BASE_URL)

params = {
    "model": "ayenaspring-pro-001",
    "messages": [{
      "content": "公安执法办案的流程有哪些？",
      "role": "user"
    }]}
response = client.chat.completions.create(**params)
1
2
3
4
5
6
7
8
9
10
请求体示例
复制
{
  "model": "ayenaspring-pro-001",
  "messages": [
    {
      "content": "公安执法办案的流程有哪些？",
      "role": "user"
    }
  ]
}
1
2
3
4
5
6
7
8
9
响应体示例
复制
{
  "created": 2224693,
  "usage": {
    "completion_tokens": 387,
    "prompt_tokens": 26,
    "total_tokens": 413
  },
  "model": "ayenaspring-pro-001",
  "id": "cmpl-50b71540fa7441489fb4d6d52af2db8a",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "公安执法办案的流程主要包括以下几个环节：\n\n1. **案件受理**：公安机关接到报案、控告、举报或发现犯罪事实和犯罪嫌疑人后，应当立即受理，依法进行初步审查，判断是否立案。...由于示例而省略部分内容...9. **监督与申诉**：检察机关有权对公安机关的执行活动进行监督，当事人及其法定代理人、近亲属对生效的判决或裁定不服的，可以依法提出申诉或上诉。\n\n以上流程中，各环节都有严格的法律规定和程序要求，确保案件处理的公正、公平、合法。"
      },
      "finish_reason": "stop"
    }
  ],
  "object": "chat.completion"
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
调用示例（流式）
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"\
  -d '{
    "messages": [
        {
            "content": "公安执法办案的流程有哪些？",
            "role": "user"
        }
    ],
    "model": "ayenaspring-pro-001",
    "stream": true
  }'
1
2
3
4
5
6
7
8
9
10
11
12
13
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY,base_url=BASE_URL)

params = {
    "model": "ayenaspring-pro-001",
    "stream": True,
    "messages": [{
      "content": "公安执法办案的流程有哪些？",
      "role": "user"
    }]}
response = client.chat.completions.create(**params)
1
2
3
4
5
6
7
8
9
10
11
请求体示例
复制
{
  "messages": [
    {
      "content": "公安执法办案的流程有哪些？",
      "role": "user"
    }
  ],
  "model": "ayenaspring-pro-001",
  "stream": true
}
1
2
3
4
5
6
7
8
9
10
响应体示例
复制
{"id":"cmpl-34d6505d510c4262927cc4e8223818d4","choices":[{"delta":{"content":null,"function_call":null,"refusal":null,"role":"assistant","tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1733129771,"model":"ayenaspring-pro-001","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"cmpl-34d6505d510c4262927cc4e8223818d4","choices":[{"delta":{"content":"我是","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1733129771,"model":"ayenaspring-pro-001","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}

...由于示例而省略部分内容...

{"id":"cmpl-34d6505d510c4262927cc4e8223818d4","choices":[{"delta":{"content":"。","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1733129780,"model":"ayenaspring-pro-001","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":null}
{"id":"cmpl-34d6505d510c4262927cc4e8223818d4","choices":[{"delta":{"content":"","function_call":null,"refusal":null,"role":null,"tool_calls":null},"finish_reason":"stop","index":0,"logprobs":null}],"created":1733129780,"model":"ayenaspring-pro-001","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":null,"usage":{"completion_tokens":86,"prompt_tokens":26,"total_tokens":112}}
1
2
3
4
5
6
7
调用示例（知识库）
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"\
  -d '{
    "messages": [
        {
            "content": "法律一般是怎么分类的？",
            "role": "user"
        },
        {
            "content": "@法律常识",
            "role": "run"
        }
    ],
    "model": "ayenaspring-pro-001"
  }' 
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
params = {
    "model": "ayenaspring-pro-001",
    "max_tokens": 2000,
    "messages": [{
      "content": "法律一般是怎么分类的？",
      "role": "user"
    },{
        "content": "@法律常识",
        "role": "run"
    }]}
response = client.chat.completions.create(**params)
1
2
3
4
5
6
7
8
9
10
11
12
13
请求体示例
复制
{
  "model": "ayenaspring-pro-001",
  "max_tokens": 2000,
  "messages": [{
    "content": "法律一般是怎么分类的？",
    "role": "user"
  },{
    "content": "@法律常识",
    "role": "run"
  }]
}
1
2
3
4
5
6
7
8
9
10
11
响应体示例
复制
{
  "id": "cmpl-898184890e694a1d8aea11573651c17d",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "法律一般可以分为以下几大类：\n\n1. **宪法**：...由于示例而省略部分内容... \n\n这些分类涵盖了法律的基本框架，不同国家或地区的具体法律体系可能在细节上有所差异。"
      },
      "logprobs": null
    },
    {
      "index": 1,
      "message": {
        "role": "docs",
        "content": "[{\"docs\":[\"【法律常识.txt】文章目录：

1. 法律的分类

2. 法律的种类

...由于示例而省略部分内容...，主刑有：管制（即对人身自由加以限制和监督）、拘役、有期徒刑、无期徒刑和死刑，附加刑有：罚金、剥夺政治权利和没收财产。\"],\"knowledgebase\":\"法律常识\"}]"
      }
    }
  ],
  "created": 1736329664,
  "model": "ayenaspring-pro-001",
  "system_fingerprint": null,
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 246,
    "prompt_tokens": 990,
    "total_tokens": 1236
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
调用示例（函数调用）
代码示例
复制
curl -s  -X POST  ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
  "messages": [
    {
      "role": "user",
      "content": "请提供距离东升科技园最近的派出所的位置坐标"
    }
  ],
  "model": "ayenaspring-pro-001",
  "stream": false,
  "tool_choice": "auto",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_policeoffice_list",
        "description": "根据当前位置，提供附近的派出所的位置列表，并按距离由近及远排序",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_position_description",
        "description": "获取当前的位置的描述信息",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    }
  ]
}'
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
复制
import openai
client = openai.Client(api_key=API_KEY,base_url=BASE_URL)
params = {
  "messages": [
    {
      "role": "user",
      "content": "请提供距离东升科技园最近的派出所的位置坐标"
    }
  ],
  "model": "ayenaspring-pro-001",
  "stream": False,
  "tool_choice": "auto",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_policeoffice_list",
        "description": "根据当前位置，提供附近的派出所的位置列表，并按距离由近及远排序",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_position_description",
        "description": "获取当前的位置的描述信息",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    }
  ]
}
response = client.chat.completions.create(**params)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
请求体示例
复制
{
  "messages": [
    {
      "role": "user",
      "content": "请提供距离东升科技园最近的派出所的位置坐标"
    }
  ],
  "model": "ayenaspring-pro-001",
  "stream": false,
  "tool_choice": "auto",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_policeoffice_list",
        "description": "根据当前位置，提供附近的派出所的位置列表，并按距离由近及远排序",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_position_description",
        "description": "获取当前的位置的描述信息",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "位置信息"
            }
          },
          "required": [
            "location"
          ]
        }
      }
    }
  ]
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
响应体示例
复制
{
  "id": "cmpl-41ac8d2ff55347f49b15b87ab31145b1",
  "choices": [
    {
      "finish_reason": "tool_calls",
      "index": 0,
      "message": {
        "role": "assistant",
        "tool_calls": [
          {
            "function": {
              "name": "get_policeoffice_list",
              "arguments": "{\"location\":\"东升科技园\"}"
            },
            "id": "0",
            "type": "function"
          }
        ]
      }
    }
  ],
  "created": 1736331269,
  "model": "ayenaspring-pro-001",
  "system_fingerprint": "fp_E8611F572CD8",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 23,
    "prompt_tokens": 399,
    "total_tokens": 422
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
调用示例（多模态）
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"\
  -d '{
           "messages": [
            {
                "role": "user",
                "content": [
                    {
                      "type": "image_url",
                      "image_url": {
                        "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJ
                        ...由于示例而省略部分内容...
                        LDL+PpCS9rgDqQOfgmdG0khoLA0XGu6SSBABzriwHO55KItyeptqCeaSSrSVj4QDnjsSbpJJKMv/2Q=="
                    }
                    },
                    {"type": "text", "text": "识别图中的文字，直接输出。"}
                ]
            }
        ],
    "model": "ayenavisual-004"
   }'
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
python示例代码
复制
import openai
client = openai.Client(api_key=API_KEY, base_url=BASE_URL)
base64 = f"data:image;base64,{base64_image}"
chat_response = client.chat.completions.create(
    model="ayenavisual-004",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": base64
                    },
                },
                {
                    "type": "text",
                    "text": "识别图中的文字，直接输出。",
                    # "text": "请详细介绍图片的内容",
                },
            ],
        },
    ],
)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
请求体示例
复制
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/...由于示例而省略部分内容...2wBDAAgGBgcGBQgHBwcJ"
          }
        },
        {"type": "text", "text": "识别图中的文字，直接输出。"}
      ]
    }
  ],
  "model": "ayenavisual-004"
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
响应体示例
复制
{
  "id": "6bd7091b8e274c7485f2d91fa73cdece",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "鲁B·325DE"
      }
    }
  ],
  "created": 1729843189,
  "model": "ayenavisual-004",
  "system_fingerprint": "fp_e8611f495d1c",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 7,
    "prompt_tokens": 15040,
    "total_tokens": 15047
  }
}
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
POST 文件会话接口（ChatFiles）
POST /chat/files/{file_id}

根据上传的文件，进行问题的问答
请求参数说明
名称	位置	类型	必选	说明
Content-Type	header	string	是	请求的内容类型
Accept	header	string	是	接收的内容类型
Authorization	header	string	否	授权码信息
body				请求体
+ model	body	string	是	要使用的模型的 ID。
+ messages	body	[object]	是	至今为止对话所包含的消息列表。
++ role	body	string	是	发起聊天内容的角色
++ content	body	[object]	是	发起的聊天内容
+ stream	body	boolean	否	默认为 false 如果设置,则像在 ChatGPT 中一样会发送部分消息增量。标记将以仅数据的服务器发送事件的形式发送。
响应参数说明
名称	类型	必填	说明
+ id	string	是	聊天完成的唯一标识符。
+ object	string	是	对象类型，始终是chat.completion。
+ model	string	是	用于完成聊天的模型。
+ created	integer	是	创建聊天完成时的Unix时间戳（以秒为单位）
+ choices	[object]	是	聊天完成选项列表。如果n大于1，则可以超过1。
++ index	integer	否	选择列表中的选择索引。
++ message	object	否	
+++ role	string	是	这条消息的作者的角色。
+++ content	string	是	消息的内容。
++ finish_reason	string	否	模型停止生成令牌的原因。
+ usage	object	是	完成请求的使用统计信息。
++ prompt_tokens	integer	是	提示符中的令牌数量。
++ completion_tokens	integer	是	生成完成中的令牌数量。
++ total_tokens	integer	是	请求中使用的令牌总数（提示+完成）。
调用示例
代码示例
shell示例代码
复制
curl -s  -X POST  ${BASE_URL}/chat/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY"\
  -d '{
    "model": "ayenaspring-pro-001",
    "messages": [
      {
        "content": "请列举一下当前法律的主要分类",
        "role": "user"
      }]
    }'
1
2
3
4
5
6
7
8
9
10
11
python示例代码
复制
import requests
import json

url = BASE_URL + "/chat/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c"
params = {
    "model": "ayenaspring-pro-001",
    "messages": [
      {
        "content": "请列举一下当前法律的主要分类",
        "role": "user"
      }]
    }

headers = {
    'Authorization': 'Bearer ' + API_KEY,  
    'Content-Type': 'application/json'  
}
response = requests.post(url, headers=headers, json=params)
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
请求体示例
复制
{
  "model": "ayenaspring-pro-001",
  "messages": [
    {
      "content": "请列举一下当前法律的主要分类",
      "role": "user"
    }]
}
1
2
3
4
5
6
7
8
响应体示例
复制
{
  "id": "cmpl-77e539a17bce497db3a29d251c0458b3",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "当前法律的主要分类包括：\n\n1. **宪法**：国家最高法律，确立基本制度与公民权利义务。\n2. **刑事法律**：\n   - **实体法**：界定犯罪行为与刑罚。\n   - **程序法**：规范刑事诉讼流程。\n3. **民事法律**：涵盖个人与组织间的民事关系，如合同、财产、家庭等。\n4. **经济法律**：管理商业活动，包括公司、税法、劳动法等。\n5. **行公安律**：规制政府行为，确保其合法性。\n\n此外，还有专门处理特定领域的法律，如婚姻法、继承法、道路交通安全法、合同法、消费者权益保护法、刑法、劳动法以及知识产权法、金融法等。这些法律共同维护社会秩序，保护公民权益。"
      },
      "logprobs": null
    }
  ],
  "created": 1736350583,
  "model": "ayenaspring-pro-001",
  "system_fingerprint": null,
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 169,
    "prompt_tokens": 578,
    "total_tokens": 747
  }
} 
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
参考数据
语言编码
编码参考《ISO 639-1语言列表》，详细编码如下：

编码	描述	编码	描述	编码	描述	编码	描述
aa	阿法尔语	fr	法语	li	林堡语	se	北萨米语
ab	阿布哈兹语	fy	弗里西亚语	ln	林加拉语	sg	桑戈语
ae	阿维斯陀语	ga	爱尔兰语	lo	老挝语	sh	塞尔维亚-克罗地亚语
af	南非语	gd	苏格兰盖尔语	lt	立陶宛语	si	僧加罗语
ak	阿坎语	gl	加利西亚语	lu	卢巴语	sk	斯洛伐克语
am	阿姆哈拉语	gn	瓜拉尼语	lv	拉脱维亚语	sl	斯洛文尼亚语
an	阿拉贡语	gu	古吉拉特语	mg	马达加斯加语	sm	萨摩亚语
ar	阿拉伯语	gv	马恩岛语	mh	马绍尔语	sn	绍纳语
as	阿萨姆语	ha	豪萨语	mi	毛利语	so	索马里语
av	阿瓦尔语	he	希伯来语	mk	马其顿语	sq	阿尔巴尼亚语
ay	艾马拉语	hi	印地语	ml	马拉亚拉姆语	sr	塞尔维亚语
az	阿塞拜疆语	ho	希里莫图语	mn	蒙古语	ss	斯瓦特语
ba	巴什基尔语	hr	克罗地亚语	mo	摩尔达维亚语	st	南索托语
be	白俄罗斯语	ht	海地克里奥尔语	mr	马拉提语	su	巽他语
bg	保加利亚语	hu	匈牙利语	ms	马来语	sv	瑞典语
bh	比哈尔语	hy	亚美尼亚语	mt	马耳他语	sw	斯瓦希里语
bi	比斯拉马语	hz	赫雷罗语	my	缅甸语	ta	泰米尔语
bm	班巴拉语	ia	国际语A	na	瑙鲁语	te	泰卢固语
bn	孟加拉语	id	印尼语	nb	书面挪威语	tg	塔吉克斯坦语
bo	藏语	ie	国际语E	nd	北恩德贝勒语	th	泰语
br	布列塔尼语	ig	伊博语	ne	尼泊尔语	ti	提格里尼亚语
bs	波斯尼亚语	ii	四川彝语（诺苏语）	ng	恩敦加语	tk	土库曼语
ca	加泰隆语	ik	依努庇克语	nl	荷兰语	tl	他加禄语
ce	车臣语	io	伊多语	nn	新挪威语	tn	塞茨瓦纳语
ch	查莫罗语	is	冰岛语	no	挪威语	to	汤加语
co	科西嘉语	it	意大利语	nr	南恩德贝勒语	tr	土耳其语
cr	克里语	iu	因纽特语	nv	纳瓦霍语	ts	宗加语
cs	捷克语	ja	日语	ny	尼扬贾语	tt	塔塔尔语
cu	古教会斯拉夫语	jv	爪哇语	oc	奥克语	tw	特威语
cv	楚瓦什语	ka	格鲁吉亚语	oj	奥吉布瓦语	ty	塔希提语
cy	威尔士语	kg	刚果语	om	奥洛莫语	ug	维吾尔语
da	丹麦语	ki	基库尤语	or	奥利亚语	uk	乌克兰语
de	德语	kj	宽亚玛语	os	奥塞梯语	ur	乌尔都语
dv	迪维希语	kk	哈萨克语	pa	旁遮普语	uz	乌兹别克语
dz	不丹语	kl	格陵兰语	pi	巴利语	ve	文达语
ee	埃维语	km	高棉语	pl	波兰语	vi	越南语
el	现代希腊语	kn	卡纳达语	ps	普什图语	vo	沃拉普克语
en	英语	ko	朝鲜语、韩语	pt	葡萄牙语	wa	沃伦语
eo	世界语	kr	卡努里语	qu	凯楚亚语	wo	沃洛夫语
es	西班牙语	ks	克什米尔语	rm	罗曼什语	xh	科萨语
et	爱沙尼亚语	ku	库尔德语	rn	基隆迪语	yi	依地语
eu	巴斯克语	kv	科米语	ro	罗马尼亚语	yo	约鲁巴语
fa	波斯语	kw	康沃尔语	ru	俄语	za	壮语
ff	富拉语	ky	吉尔吉斯语	rw	卢旺达语	zh	中文、汉语
fi	芬兰语	la	拉丁语	sa	梵语	zu	祖鲁语
fj	斐济语	lb	卢森堡语	sc	萨丁尼亚语		
fo	法罗语	lg	卢干达语	sd	信德语		
模型参数
以下是示例信息，具体信息可使用"模型列表检索"接口获取

模型	英文名称	模型参数	上下文长度
公安专业大模型1.0（百度版）	GA1.0-Pro-B	70B	8K
公安专业大模型1.0（阿里版）	GA1.0-Pro-A	72B	128K
公安专业大模型1.0（科大讯飞版）	GA1.0-Pro-K	70B	8K
响应码
类别	状态码	描述
1xx	100	Continue：继续。客户端应继续其请求。
101	Switching Protocols：切换协议。服务器根据客户端的请求切换协议。
2xx	200	OK：成功。请求已成功被服务器接收、理解、并接受。
201	Created：已创建。请求成功并且服务器已创建了新的资源。
202	Accepted：已接受。服务器已接受请求，但尚未处理。
204	No Content：无内容。服务器成功处理了请求，但没有返回任何内容。
3xx	301	Moved Permanently：永久移动。请求的资源已被永久移动到新位置。
302	Found：临时移动。请求的资源临时从不同的URI响应请求。
304	Not Modified：未修改。自从上次请求后，请求的资源未修改过。
4xx	400	Bad Request：错误请求。服务器无法理解请求，因为它的语法错误。
401	Unauthorized：未授权。请求未授权。
403	Forbidden：禁止访问。服务器理解请求但拒绝执行。
404	Not Found：未找到。服务器找不到请求的资源。
408	Request Timeout：请求超时。服务器等待客户端发送请求时超时。
5xx	500	Internal Server Error：内部服务器错误。服务器遇到了阻止其完成请求的意外情况。
501	Not Implemented：未实现。服务器不支持请求的功能，无法完成请求。
502	Bad Gateway：错误网关。服务器作为网关或代理，从上游服务器收到了无效响应。
503	Service Unavailable：服务不可用。服务器目前无法使用（由于超载或停机维护）。
504	Gateway Timeout：网关超时。服务器作为网关或代理，但是没有及时从上游服务器收到请求。