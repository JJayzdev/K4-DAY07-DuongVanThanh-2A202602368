# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** AIGAN
**Thành viên:** Hồ Ngọc Mai, Mai Văn Trường, Nguyễn Viết Đức, Dương Văn Thành
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách hủy đơn, đổi trả, hoàn tiền và bảo vệ người mua/người bán trên eBay.

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề này vì các chính sách eBay có nguồn công khai, nội dung thực tế và chứa nhiều điều kiện, ngoại lệ, con số cùng mốc thời gian phù hợp để đánh giá chất lượng chunking và truy xuất. Corpus được tách cân bằng thành ba tài liệu cho người mua và ba tài liệu cho người bán, nhờ đó có thể kiểm chứng rõ tác dụng của `metadata_filter` theo `audience` thay vì chỉ so sánh độ tương đồng ngữ nghĩa. Các câu trả lời cũng có thể đối chiếu trực tiếp với URL nguồn, giúp việc đánh giá kết quả RAG minh bạch và hạn chế suy diễn.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Hủy đơn hàng dành cho người mua | [eBay Help](https://www.ebay.com/help/buying/default/cancel-order?id=4004) | 2026-09-20 / `not-stated` | 2.117 | `audience=buyer`, `category=order-cancellation`, `language=en` |
| 2 | Xử lý khi người mua chưa nhận được hàng | [eBay Help](https://www.ebay.com/help/buying/searching/item-values?id=4042) | 2026-09-20 / `not-stated` | 4.766 | `audience=buyer`, `category=item-not-received`, `language=en` |
| 3 | Tổng quan đổi trả và hoàn tiền cho người mua | [eBay Help](https://www.ebay.com/help/returns-refunds/buying/returns-missing-items-refunds-buyers?id=4008) | 2026-09-20 / `not-stated` | 3.254 | `audience=buyer`, `category=returns-refunds`, `language=en` |
| 4 | Yêu cầu eBay can thiệp dành cho người bán | [eBay Help](https://www.ebay.com/help/selling/managing-returns-refunds/ask-ebay-to-step-in?id=4702) | 2026-09-20 / `not-stated` | 4.141 | `audience=seller`, `category=dispute-resolution`, `language=en` |
| 5 | Cơ chế bảo vệ người bán eBay | [eBay Help](https://www.ebay.com/help/policies/selling-policies/seller-performance-policy?id=4345) | 2026-09-20 / `not-stated` | 14.388 | `audience=seller`, `category=seller-protection`, `language=en` |
| 6 | Thiết lập chính sách đổi trả cho người bán | [eBay Help](https://www.ebay.com/help/Selling/Returns_Refunds/Setting_up_your_return_policy?id=4368) | 2026-09-20 / `not-stated` | 6.179 | `audience=seller`, `category=returns-policy`, `language=en` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [ ] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [ ] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `ebay-buyer-cancel-order` | Định danh ổn định tài liệu, liên kết chunk với nguồn và hỗ trợ xóa/cập nhật đúng tài liệu. |
| `title` | string | `Hủy đơn hàng dành cho người mua` | Cung cấp ngữ cảnh ngắn gọn để hiển thị và giải thích kết quả truy xuất. |
| `source_url` | URL/string | `https://www.ebay.com/help/...` | Cho phép kiểm chứng câu trả lời với trang chính sách gốc. |
| `retrieved_at` | date (`YYYY-MM-DD`) | `2026-09-20` | Cho biết thời điểm thu thập để đánh giá độ mới của dữ liệu. |
| `document_version` | string | `not-stated` | Theo dõi phiên bản/ngày hiệu lực khi nguồn có nêu; dùng `not-stated` khi không có, tránh tự đặt số hiệu. |
| `audience` | enum (`buyer`, `seller`) | `buyer` | Cho phép pre-filter theo đối tượng; corpus hiện có 3 tài liệu buyer và 3 tài liệu seller. |
| `category` | string/enum | `order-cancellation` | Thu hẹp tìm kiếm theo nghiệp vụ như hủy đơn, đổi trả, tranh chấp hoặc bảo vệ người bán. |
| `language` | ISO language code | `en` | Hỗ trợ chọn đúng ngôn ngữ của corpus và mô hình embedding phù hợp. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Xử lý khi người mua chưa nhận được hàng | FixedSizeChunker (`fixed_size`) | 10 | 492,4 | Trung bình — có thể cắt giữa câu/ý. |
| Xử lý khi người mua chưa nhận được hàng | SentenceChunker (`by_sentences`) | 15 | 295,4 | Tốt — giữ nguyên câu nhưng một số chunk ngắn. |
| Xử lý khi người mua chưa nhận được hàng | RecursiveChunker (`recursive`) | 11 | 404,9 | Tốt — ưu tiên ranh giới đoạn và câu. |
| Cơ chế bảo vệ người bán eBay | FixedSizeChunker (`fixed_size`) | 32 | 488,7 | Trung bình — kích thước đều nhưng có thể đứt điều kiện. |
| Cơ chế bảo vệ người bán eBay | SentenceChunker (`by_sentences`) | 20 | 701,4 | Khá — nguyên câu nhưng có chunk vượt ngưỡng 500 ký tự. |
| Cơ chế bảo vệ người bán eBay | RecursiveChunker (`recursive`) | 35 | 400,4 | Tốt — giữ các cụm nội dung gần nhau và không vượt ngưỡng. |
| Thiết lập chính sách đổi trả cho người bán | FixedSizeChunker (`fixed_size`) | 13 | 497,2 | Trung bình — có nguy cơ tách danh sách chính sách. |
| Thiết lập chính sách đổi trả cho người bán | SentenceChunker (`by_sentences`) | 11 | 530,8 | Khá — giữ câu nhưng có chunk dài hơn ngưỡng. |
| Thiết lập chính sách đổi trả cho người bán | RecursiveChunker (`recursive`) | 16 | 364,6 | Tốt — tách theo ranh giới tự nhiên và gom mảnh nhỏ. |

> Baseline dùng `chunk_size=500` và chỉ so sánh phần thân tài liệu; YAML frontmatter đã được loại khỏi đầu vào trước khi gọi `compare()`.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Dương Văn Thành**
- **Loại chiến lược:** Custom — `HeadingChunker(chunk_size=700)`
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách thường được tổ chức theo các heading, nên mỗi section được xem là một đơn vị ngữ nghĩa trước khi xét giới hạn độ dài. Section vượt 700 ký tự được chia tiếp bằng `RecursiveChunker`, đồng thời heading được gắn lại vào mọi chunk con để các mảnh phía sau không mất ngữ cảnh; với 6 tài liệu hiện tại, chiến lược tạo 58 chunk và chunk dài nhất là 696 ký tự.
- **Code snippet (nếu custom):**
```python
chunker = HeadingChunker(chunk_size=700)
for path in corpus_paths:
    metadata, content = parse_markdown(path)  # frontmatter không đi vào chunker
    for i, chunk in enumerate(chunker.chunk(content)):
        documents.append(Document(
            id=f"{path.stem}#{i}", content=chunk,
            metadata={**metadata, "doc_id": path.stem, "chunk_index": i},
        ))
```

**Thành viên 2 — Hồ Ngọc Mai**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=700, overlap=70)`
- **Mô tả & lý do chọn:** Là đường cơ sở có kích thước ổn định và overlap 10% để hạn chế mất ngữ cảnh tại biên chunk. Nhánh này tạo 54 chunk và đạt 5/10 theo answer marker.
- **Code snippet (nếu custom):** Không dùng custom chunker.

**Thành viên 3 — Mai Văn Trường**
- **Loại chiến lược:** `SentenceChunker(max_sentences_per_chunk=3)`
- **Mô tả & lý do chọn:** Giữ nguyên ranh giới câu và dấu câu để tránh chunk bị cụt ý. Nhánh này tạo 69 chunk và đạt 3/10; độ dài không đều làm một số điều kiện bị tách khỏi danh sách liên quan.
- **Code snippet (nếu custom):** Không dùng custom chunker.

**Thành viên 4 — Nguyễn Viết Đức**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=700)`
- **Mô tả & lý do chọn:** Ưu tiên ranh giới đoạn, dòng, câu và từ, sau đó gom các mảnh nhỏ tới sát ngưỡng. Nhánh này tạo 57 chunk và đạt 7/10, cao nhất trong lần đo.
- **Code snippet (nếu custom):** Không dùng custom chunker.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Hồ Ngọc Mai | Fixed (`700/70`) | 5/10 | Kích thước tương đối đều; Q2 và Q3 đúng top-1. | Có thể cắt tách marker khỏi chunk đúng chủ đề; Q1 và Q5 đúng file nhưng không có đáp án. |
| Mai Văn Trường | Sentence (`3 câu/chunk`) | 3/10 | Q1 sau filter lấy được chunk đáp án ở hạng 3; bảo toàn dấu câu. | Chunk không đều; Q3/Q4/Q5 lấy đúng file nhưng sai section. |
| Nguyễn Viết Đức | Recursive (`700`) | **7/10** | Tốt nhất trong lần đo; Q2–Q4 có answer-bearing chunk, trong đó Q2–Q4 đúng hoặc gần top-1. | Q1 vẫn sai section; Q5 có đáp án ở hạng 2. |
| Dương Văn Thành | Heading + recursive (`700`) | 5/10 | Giữ heading trong mọi chunk con; Q2 và Q3 đúng top-1. | Corpus chỉ có heading cấp tài liệu nên nhiều chunk cùng tiêu đề; Q1 và Q4 đúng file nhưng sai section. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Trong lần đo này, `RecursiveChunker(chunk_size=700)` tốt nhất với 7/10, cao hơn Fixed và Heading (5/10) cùng Sentence (3/10). Recursive tận dụng ranh giới đoạn/câu và gom mảnh nhỏ nên giữ được nhiều cụm điều kiện–kết luận trong cùng chunk; Heading chưa thắng vì dữ liệu hiện chủ yếu chỉ có heading cấp tài liệu, khiến việc lặp lại cùng tiêu đề làm các section trong một file có điểm gần nhau nhưng không đảm bảo section chứa đáp án được xếp cao.

**Failure case quan sát ở mục 2:** Với Heading, Q1 có đúng `doc_id` ở hạng 2 nhưng chunk `#2` không chứa mốc “within 3 calendar days” nằm trong `#1`; Q4 cũng lấy `#2` thay vì chunk đáp án `#3`. Vì vậy phép chấm chỉ theo `doc_id` cho kết quả 5/5 trong khi chấm theo nội dung chỉ đạt 3/5 (5/10 điểm); hướng sửa là bổ sung heading cấp section và overlap khi section dài bị recursive-split.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Sau khi yêu cầu hủy được gửi, bên còn lại có bao lâu để phản hồi? | Người bán có **3 ngày theo lịch** để chấp nhận hoặc từ chối yêu cầu hủy. Query này dùng `metadata_filter={"audience": "buyer"}` để tránh lẫn với thời hạn **3 ngày làm việc** trong quy trình phía người bán. | `ebay-buyer-cancel-order#1` |
| 2 | Người mua phải báo chưa nhận được hàng trong thời hạn bao lâu để đủ điều kiện bảo vệ? | Trong vòng **30 ngày theo lịch** kể từ ngày giao hàng dự kiến. | `ebay-buyer-item-not-received#2` |
| 3 | Điều kiện nào để Top Rated Seller được hưởng bảo vệ của eBay? | Người bán phải có cấp Top Rated Seller, ở Mỹ hoặc Canada, không có service metric mức “Very High”, đăng mặt hàng trên eBay.com và listing cho phép trả hàng từ **30 ngày** trở lên. | `ebay-seller-protections#1` |
| 4 | Người mua thực hiện các bước nào để báo một món hàng chưa đến? | Mở Purchases, tìm món hàng, chọn More actions, chọn “I didn't receive it”, chọn cách xử lý mong muốn, thêm lời nhắn nếu cần rồi gửi yêu cầu. | `ebay-buyer-item-not-received#3` |
| 5 | Người bán có thể chọn những thời hạn và hình thức trả hàng nào? | Không nhận trả hàng; trả hàng 30 ngày do người mua trả phí; miễn phí 30 ngày; người mua trả phí 60 ngày; hoặc miễn phí 60 ngày. Một số danh mục cho phép thời hạn 14 ngày. | `ebay-seller-return-policy#0`, `#1` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời hạn phản hồi yêu cầu hủy | Heading + recursive, lọc `audience=buyer` | **Không** — đúng file ở hạng 2 nhưng sai section | Top-3 có `ebay-buyer-cancel-order#2`, còn marker `within 3 calendar days` nằm ở `#1`; 0/2. |
| 2 | Hạn báo chưa nhận được hàng | Heading + recursive | Có — gold ở hạng 1, score `0,6614` | Truy xuất đúng `ebay-buyer-item-not-received`. |
| 3 | Điều kiện bảo vệ Top Rated Seller | Heading + recursive, lọc `audience=seller` | Có — gold ở hạng 1, score `0,8365` | Cả ba kết quả đầu đều thuộc tài liệu gold. |
| 4 | Quy trình báo hàng chưa đến | Heading + recursive, lọc `audience=buyer` | **Không** — đúng file ở hạng 1 nhưng sai section | Top-1 là `ebay-buyer-item-not-received#2`, còn marker `I didn't receive it` nằm ở `#3`; 0/2. |
| 5 | Các lựa chọn thời hạn/hình thức trả hàng | Heading + recursive, lọc `audience=seller` | Có — answer-bearing chunk ở hạng 2, score `0,6180` | Đúng file ở hạng 1 nhưng marker `30-day buyer-paid returns` chỉ xuất hiện ở hạng 2; 1/2. |

**Kết quả hai mức:** document-level đạt **5/5**, nhưng chỉ **3/5** query có chunk thật sự chứa marker đáp án trong top-3; điểm content-level là **5/10**. Backend sử dụng là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; không dùng `MockEmbedder`.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, nhưng hiệu quả phụ thuộc chunker. Với Q1, filter làm thay đổi top-3 ở cả bốn chiến lược; riêng Sentence đưa answer-bearing chunk từ ngoài top-3 lên hạng 3, còn Fixed/Recursive/Heading chỉ đưa đúng **file** vào top-3 nhưng vẫn sai section. Ở Q5, filter `seller` đưa đúng file từ hạng 3 lên hạng 1 với Heading, nhưng chunk chứa danh sách đầy đủ nằm ở hạng 2; đây là bằng chứng rằng metadata cải thiện precision theo đối tượng nhưng không thay thế việc chấm nội dung chunk.

#### A/B bắt buộc cho Q1 — có và không lọc `audience=buyer`

| Chiến lược | Không lọc — top-3 `doc_id#chunk` | Có lọc — top-3 `doc_id#chunk` | Rank chunk chứa đáp án |
|---|---|---|---|
| Fixed | `item-not-received#5`, `seller-protections#2`, `seller-protections#4` | `item-not-received#5`, `buyer-cancel#2`, `buyer-returns#3` | Không có → Không có |
| Sentence | `seller-protections#2`, `#9`, `#4` | `item-not-received#9`, `#10`, `buyer-cancel#3` | Không có → **3** |
| Recursive | `item-not-received#5`, `seller-step-in#4`, `seller-protections#4` | `item-not-received#5`, `buyer-cancel#2`, `buyer-returns#3` | Không có → Không có |
| Heading | `seller-step-in#6`, `buyer-returns#3`, `seller-step-in#1` | `buyer-returns#3`, `buyer-cancel#2`, `item-not-received#6` | Không có → Không có |

#### Failure case và hướng sửa

**Câu hỏi hỏng:** Q1 với Heading — document-level báo thành công vì `ebay-buyer-cancel-order#2` đứng hạng 2, nhưng chunk này không chứa thời hạn `within 3 calendar days`; đáp án thực nằm ở chunk `#1`. Q4 cũng gặp cùng kiểu lỗi: top-1 đúng tài liệu nhưng marker quy trình nằm ở chunk kế tiếp.

**Nguyên nhân:** cosine ưu tiên độ giống chủ đề, không đo trực tiếp chunk có chứa con số/bước trả lời hay không. Corpus hiện chỉ có heading cấp tài liệu, nên mọi chunk con được gắn cùng một heading; đồng thời chiến lược không overlap khiến thông tin ở chunk liền kề chỉ có một cơ hội lọt top-k.

**Đề xuất sửa:** chuẩn hóa thêm heading cấp section trong dữ liệu sạch, hoặc cho `HeadingChunker` dùng overlap khi recursive-split để giữ liền điều kiện với mốc thời gian/quy trình. Có thể rerank top-k bằng tín hiệu lexical cho số, đơn vị thời gian và action phrase, nhưng vẫn phải giữ metadata filter trước similarity search.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Document-level hit 5/5 đã thổi phồng chất lượng của Heading: kiểm marker trong nội dung chỉ còn 3/5 và 5/10 điểm.
> - Recursive đạt 7/10, tốt hơn Fixed/Heading (5/10) và Sentence (3/10), cho thấy việc giữ ranh giới tự nhiên và gom mảnh nhỏ quan trọng hơn chỉ gắn tiêu đề chung.
> - Metadata filter cải thiện precision theo đối tượng nhưng không bảo đảm đúng section: ở Q1, chỉ Sentence đưa chunk đáp án vào top-3 sau khi lọc; ba chiến lược còn lại vẫn lấy sai section.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng corpus và cùng embedding, chiến lược chia chunk làm score biến động từ 3/10 đến 7/10 vì nó quyết định điều kiện, con số và thao tác có nằm chung một đơn vị truy xuất hay không. Failure case Q1/Q4 của Heading cho thấy chunk đúng chủ đề hoặc đúng file chưa đủ: nếu đáp án nằm ở section liền kề ngoài top-3 thì agent vẫn thiếu căn cứ và có nguy cơ trả lời sai.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ chuẩn hóa các tiêu đề cấp section (`##`) ngay trong bước làm sạch và thêm overlap nhỏ khi một section dài phải chia tiếp, để mỗi mốc thời gian/quy trình có nhiều hơn một cơ hội xuất hiện trong top-k. Benchmark sẽ luôn chấm đồng thời `doc_id` và answer marker, giữ A/B filter, đồng thời thử rerank bằng tín hiệu lexical cho số, đơn vị thời gian và cụm thao tác trước khi kết luận chiến lược tốt nhất.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10/ 10 |
| Thiết kế chiến lược (Strategy Design) | 15/ 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10/ 10 |
| Thuyết trình (Demo) | 5/ 5 |
| **Tổng phần nhóm** | **40/ 40** |
