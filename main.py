#Thư viện
import os
#os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
import re
import transformers 
import torch 
import pandas as pd
import pprint
from pypdf import PdfReader
from transformers import pipeline
from paddleocr import PaddleOCR
from huggingface_hub import login
from pymongo import MongoClient

# Hàm đọc file PDF
def read_pdf(file_path):
    reader = PdfReader(file_path)
    page = reader.pages[0]
    return page.extract_text()

# Hàm trích xuất text từ hình ảnh

def paddleOCR(image_path, lang):
    ocr = PaddleOCR(lang = lang)
    result_en = ocr.ocr(image_path = image_path,cls = True)
    print("Ket qua OCR :")
    for line in result_en[0]:
        print(f"Văn bản :{line[0][1]} | Độ Tin Cậy: {[1][1]}")

# Hàm lấy văn bản từ file PDF hoặc hình ảnh
def get_text(types, image_path=False, file_path=False):
    if types == 'pdf':
        return read_pdf(file_path)
    elif types == 'image':
        return paddleOCR(image_path, 'en')
    else:
        print("File không hợp lệ..!!")

# Hàm xử lý các file CV trong thư mục
def process_cv(folder_path):
    all_cv_text = []
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if file_name.endswith(".pdf"):
            cv_text = get_text("pdf", file_path=file_path)
            all_cv_text.append(cv_text)
        elif file_name.endswith(".png") or file_name.endswith(".jpg"):
            cv_text = get_text("image", image_path=file_path)
            all_cv_text.append(cv_text)
    return all_cv_text

#thay đổi token
#login(token=" điền Token")

# Model Llama
model_id = "meta-llama/Llama-3.2-3B-Instruct"
device = 0
pipeline = transformers.pipeline("text-generation", model=model_id, device=device, model_kwargs={'torch_dtype': torch.bfloat16})

# Hàm trích xuất thông tin từ nội dung CV
def extract_cv_info(cv_text):
    result = {}

    # Trích xuất tên ứng viên
    name_match = re.search(r"([A-Za-z\s]+)", cv_text)
    if name_match:
        # Clean the name by removing unwanted characters such as '\nK'
        name = name_match.group(0).strip()
        name = re.sub(r'\n.*', '', name)  # Remove anything after newline
        result['Họ và Tên'] = name
    else:
        result['Họ và Tên'] = "Không xác định"

    # Trích xuất các điều kiện
    conditions = []

    # Kiểm tra các điều kiện
    if 'Python' in cv_text:
        conditions.append('Biết Python: Có')
    else:
        conditions.append('Thiếu Biết Python')

    if 'English' in cv_text and re.search(r'English\s*[:|-]?\s*([A-Za-z\s]+)', cv_text):
        english_match = re.search(r'English\s*[:|-]?\s*([A-Za-z\s]+)', cv_text)
        conditions.append(f'Tiếng Anh: {english_match.group(1)}')
    else:
        conditions.append('Thiếu Tiếng Anh')

    if 'Computer Vision' in cv_text:
        conditions.append('Computer Vision: Có')
    else:
        conditions.append('Thiếu Computer Vision')

    if 'Natural Language Processing' in cv_text:
        conditions.append('Natural Language Processing (NLP): Có')
    else:
        conditions.append('Thiếu Natural Language Processing (NLP)')

    # Kiểm tra GPA
    if 'GPA' in cv_text and re.search(r'GPA\s*[:|-]?\s*(\d+\.\d+)', cv_text):
        gpa = float(re.search(r'GPA\s*[:|-]?\s*(\d+\.\d+)', cv_text).group(1))
        if gpa >= 2.8:
            conditions.append('GPA trên 2.8: Có')
        else:
            conditions.append(f'Thiếu GPA trên 2.8 (GPA {gpa})')
    else:
        conditions.append('Thiếu GPA trên 2.8')

    # Kiểm tra kinh nghiệm làm việc
    if re.search(r'(\d+)\s*(months|year)', cv_text):
        experience = int(re.search(r'(\d+)\s*(months|year)', cv_text).group(1))
        if experience > 8:
            conditions.append(f'Có {experience} năm kinh nghiệm (trên 8 tháng)')
        else:
            conditions.append('Thiếu Kinh nghiệm làm việc trên 8 tháng')
    else:
        conditions.append('Thiếu Kinh nghiệm làm việc trên 8 tháng')

    result['Điều kiện đáp ứng'] = conditions

    # Tính số điều kiện đáp ứng
    num_conditions_met = sum(1 for cond in conditions if cond.endswith(": Có"))

    # Cập nhật yêu cầu đáp ứng
    if num_conditions_met == len(conditions):
        result['Đáp ứng yêu cầu'] = f'Đáp ứng tất cả {num_conditions_met} yêu cầu'
    else:
        result['Đáp ứng yêu cầu'] = f'Đáp ứng {num_conditions_met} yêu cầu'

    return result


# Xử lý tất cả các CV trong thư mục và trả về kết quả
def process_all_cv(folder_path):
    all_cv_texts = process_cv(folder_path)
    cv_results = []
    for cv_text in all_cv_texts:
        extracted_info = extract_cv_info(cv_text)
        cv_results.append(extracted_info)
    return cv_results

#Lưu kết quả đầu ra dạng file CSV
def save_results_to_csv(results, filename):
    # Chuyển kết quả thành DataFrame
    df = pd.DataFrame(results)
    # Lưu vào file CSV
    df.to_csv(filename, index=False)

# ĐƯA DỮ LIỆU LÊN DATABASE
def save_to_mongodb(result):
    connections = "mongodb+srv://TrongLyo:Trong8602@tronglyo.ikzzj.mongodb.net/CV_TEXT?retryWrites=true&w=majority"
    client = MongoClient(connections)
    #Tên database (Folder) và collection (Table) đã tạo trên mongodb compass
    db = client['CV_TEXT'] #Database 
    collection = db['OCR-LLAMA'] #Collection
    #Thêm dữ liệu đầu ra vào mongodb
    collection.insert_many(result)
    print("Đã đưa dữ liệu lên Mongocompass Thành Công ..!!")
    
    
    

# Chạy qua tất cả các CV và lưu kết quả vào CSV
if __name__ == "__main__":
    folder_path = "E:\\LLama_OCR\\File_cv\\Dataset_cv"
    #folder_path = "app/File_cv/Dataset_cv"
    user_request = """
        Từ nội dung trong CV:
        xác định họ và tên (Full Name In CV) ứng viên cùng các điều kiện họ đáp ứng từ yêu cầu: Biết Python, Tiếng Anh, Computer Vision, Natural Language Processing (NLP), GPA trên 2.8, Kinh nghiệm làm việc trên 8 tháng.
        In ra họ và tên và các điều kiện đáp ứng. Mỗi CV TRẢ LỜI 1 LẦN
                    """

    # Lấy kết quả từ tất cả các CV trong thư mục
    cv_results = process_all_cv(folder_path)
    
    #lưu kết quả vào Mgdb
    save_to_mongodb(cv_results)
    
    # Lưu kết quả vào CSV
    save_results_to_csv(cv_results, "E:\\LLama_OCR\\File_cv\\results_cv.csv")
    #save_results_csv(cv_results,"app/File_cv/results_cv.csv")  
    
    # In ra kết quả
    pprint.pprint(cv_results)
