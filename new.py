# 导入SDK，发起请求
from openai import OpenAI

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key="VSlATEQWESUBDNMgkfgi:AWJyQzcyxyDENkqMEFhe", 
    base_url='https://spark-api-open.xf-yun.com/v1'  # 指向讯飞星火的请求地址
)

# 发起请求
completion = client.chat.completions.create(
    model='generalv3',  # 指定请求的版本
    messages=[
        {
            "role": "user",
            "content": '中医分为哪几类'
        }
    ]
)

# 打印结果
print(completion.choices[0].message)