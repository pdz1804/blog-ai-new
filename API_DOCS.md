# Tài liệu API: Quản lý Item & Upload File (Presigned URL)

**Base URL**: https://items-service-83689773481.asia-southeast1.run.app

Tài liệu này mô tả chi tiết 2 API quan trọng cho quy trình: 
1. **Tải tệp đa phương tiện/ảnh** lên hệ thống đám mây (Direct Cloud Upload).
2. **Tạo dữ liệu Text cho Item (Bài viết/Tài liệu)** sau khi đã có đường dẫn ảnh.

---

## 1. API: Xin URL Tải File (Presigned URL)
API này sinh ra một đường dẫn khả dụng trong vòng 15 phút, cho phép Frontend ủy quyền đẩy trực tiếp file/ảnh lên Google Cloud Storage.

- **Endpoint**: /api/v1/upload/presign
- **Method**: POST
- **Headers**: Content-Type: application/json

### Payload Request (Input)
| Field | Type | Bắt buộc | Mô tả |
| :--- | :--- | :---: | :--- |
| ilename | string | **Có** | Tên file gốc của người dùng (giữ lại đuôi mở rộng như .jpg, .png). Tối đa 200 ký tự. |
| content_type| string | Không | Định dạng MIME của file ảnh. Mặc định là image/jpeg. |

**Ví dụ Input:**
`json
{
  "filename": "my_avatar.png",
  "content_type": "image/png"
}
`

### Response (Output)
| Field | Type | Mô tả |
| :--- | :--- | :--- |
| url | string | Đường dẫn chứa Token dùng để gọi HTTP PUT tải file lên ở phía Frontend. |
| object_name | string | Tên tệp đã được Server random lại (VD: uploads/9b1abc...png). |
| method | string | HTTP Method bắt buộc phải sử dụng để upload (Luôn là PUT). |

💡 **Lưu ý Frontend:** Sau khi gọi API này, Frontend dùng HTTP PUT đẩy file lên url được cấp (Headers phải set Content-Type y hệt lúc xin). Upload xong, ảnh sẽ public ở: \https://storage.googleapis.com/blog-images-default-bucket/{object_name}\.

---

## 2. API: Tạo mới Item (Bài viết/Sản phẩm)
API này lưu trữ toàn bộ văn bản và hình ảnh của thẻ Item. Dữ liệu sẽ lưu qua Database (Firestore) đồng thời nạp vào Engine tìm kiếm (Vertex AI).

- **Endpoint**: /api/v1/items
- **Method**: POST
- **Headers**: Content-Type: application/json

### Payload Request (Input)
| Field | Type | Bắt buộc | Mô tả & Ràng buộc |
| :--- | :--- | :---: | :--- |
| 	itle | string | **Có** | Tiêu đề của Item (1 - 300 ký tự). |
| description | string | Không | Nội dung chi tiết bài viết (Tối đa 5000 ký tự). Có thể là Markdown/HTML. |
| bstraction | string | Không | Đoạn tóm tắt nội dung (Tối đa 5000 ký tự, mặc định ""). |
| 	ags | rray[string]| Không | Danh sách các thẻ (VD: ["AI", "Tech"]). Mặc định là []. |
| uthor_id | string | Không | ID của tác giả bài viết. |
| uthor_name | string | Không | Tên tác giả (Tối đa 200 ký tự). |
| source | string | Không | Nguồn trích dẫn (Tối đa 200 ký tự). |
| url | string | Không | Đường dẫn đính kèm. **Có thể dùng để lưu Link Ảnh Public lấy được từ Bước 1** (Tối đa 2000 ký tự). |
| citations | rray[string]| Không | Danh sách các URL dẫn chứng tham khảo thêm. |

**Ví dụ Input (Tạo Item sau khi đã có link web ảnh):**
`json
{
  "title": "Ứng dụng AI vào đời sống",
  "abstraction": "Bài viết tóm tắt về cách AI thay đổi tương lai...",
  "description": "Nội dung chi tiết dài hàng ngàn chữ ở đây...",
  "tags": ["AI", "Future", "2026"],
  "author_name": "Nguyen Van A",
  "url": "https://storage.googleapis.com/blog-images-default-bucket/uploads/9b1abc123.png"
}
`

### Response (Output)
| Field | Type | Mô tả |
| :--- | :--- | :--- |
| id | string | ID (UUID v4) của bài viết ngẫu nhiên do Backend tạo. |
| 	itle | string | Tiêu đề. |
| 	ags | rray | Danh sách thẻ. |
| created_date | string | Ngày giờ tạo bản ghi (Định dạng ISO 8601). |
| updated_date | string | Ngày giờ cập nhật bản ghi cuối cùng. |
| ... | ... | Trả về kèm các trường dữ liệu mà bạn đã gửi lên (author_name, url, description, v.v). |

**Ví dụ Output:**
`json
{
  "id": "e2ba345f-7c30-4e39-a9a3-5c8e3125a07c",
  "title": "Ứng dụng AI vào đời sống",
  "description": "Nội dung chi tiết dài hàng ngàn chữ ở đây...",
  "abstraction": "Bài viết tóm tắt về cách AI thay đổi tương lai...",
  "tags": ["AI", "Future", "2026"],
  "author_id": null,
  "author_name": "Nguyen Van A",
  "source": null,
  "url": "https://storage.googleapis.com/blog-images-default-bucket/uploads/9b1abc123.png",
  "citations": null,
  "created_date": "2026-04-06T08:25:34.123456Z",
  "updated_date": "2026-04-06T08:25:34.123456Z"
}
`
