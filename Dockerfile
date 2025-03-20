# Sử dụng image Python 3.9 slim làm base image
FROM python:3.9-slim

# Đặt thư mục làm việc trong container là /app
WORKDIR /app

# Cài đặt libGL để giải quyết lỗi khi sử dụng OpenCV
RUN apt-get update && apt-get install -y libgl1-mesa-glx
RUN apt-get update && apt-get install -y libglib2.0-0



# Sao chép file requirements.txt vào container
COPY requirements.txt /app/requirements.txt

# Cài đặt các dependencies từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt



# Sao chép toàn bộ mã nguồn vào thư mục /app trong container
COPY . /app
# Lệnh mặc định khi chạy container sẽ là chạy file llama.py bằng Python
CMD ["python", "main.py"]
