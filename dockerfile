# 使用官方 Python 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录在容器内
WORKDIR /app

# 将依赖信息复制到容器内
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将当前目录下的代码复制到容器内的工作目录
COPY . .

# 声明运行时容器提供服务的端口
EXPOSE 8000

# 定义环境变量
ENV MODULE_NAME="app.main"
ENV VARIABLE_NAME="app"

# 使用 uvicorn 运行 fastapi 应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
