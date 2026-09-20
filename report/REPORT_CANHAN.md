# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Dương Văn Thành
**Nhóm:** AIGANG
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity cao nghĩa là hai vector embedding có hướng gần nhau trong không gian vector, cho thấy hai đoạn văn biểu đạt ý nghĩa hoặc ngữ cảnh tương tự. Giá trị càng gần 1 thì mức tương đồng ngữ nghĩa thường càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Người mua có thể yêu cầu hoàn tiền nếu kiện hàng không đến.
- Câu B: Khách hàng được quyền lấy lại tiền khi đơn hàng không được giao.
- Tại sao tương đồng: Hai câu dùng từ vựng khác nhau (`người mua`/`khách hàng`, `hoàn tiền`/`lấy lại tiền`, `không đến`/`không được giao`) nhưng cùng diễn đạt quyền được hoàn tiền khi không nhận được hàng.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người bán phải phản hồi yêu cầu đổi trả trong ba ngày làm việc.
- Câu B: Mô hình embedding biến văn bản thành vector số.
- Tại sao khác: Câu A nói về thời hạn xử lý trong chính sách thương mại điện tử, còn câu B mô tả một kỹ thuật biểu diễn dữ liệu trong học máy; hai câu không cùng chủ đề hay mục đích.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine tập trung vào góc giữa hai vector nên đo được sự gần nhau về hướng ngữ nghĩa và ít bị ảnh hưởng bởi độ lớn vector, vốn có thể thay đổi theo độ dài hoặc cường độ của văn bản. Khoảng cách Euclid đo khoảng cách tuyệt đối nên hai vector cùng hướng nhưng khác độ lớn vẫn có thể bị xem là xa nhau; vì vậy cosine thường phù hợp hơn để xếp hạng mức tương đồng của text embedding.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Bước dịch giữa hai chunk là `500 − 50 = 450` ký tự. Áp dụng công thức: `ceil((10.000 − 50) / (500 − 50)) = ceil(9.950 / 450) = ceil(22,111...) = 23`.
> *Đáp án:* **23 chunks**. Kết quả đã được kiểm tra bằng `len(FixedSizeChunker(chunk_size=500, overlap=50).chunk("x" * 10000))` và nhận được `23`.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, số chunk tăng thành `ceil((10.000 − 100) / (500 − 100)) = ceil(9.900 / 400) = 25`; chạy `FixedSizeChunker` cũng trả về `25`. Overlap lớn hơn giúp giữ ngữ cảnh tại ranh giới chunk, giảm nguy cơ tách rời điều kiện và kết luận, nhưng làm tăng dữ liệu trùng lặp, chi phí embedding và khả năng các chunk gần giống nhau cùng chiếm top-k.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` với positive lookbehind để tách tại khoảng trắng ngay sau dấu kết câu, nhờ đó vẫn giữ dấu câu trong nội dung. Text rỗng trả về `[]`, còn các câu được strip rồi gom theo `max_sentences_per_chunk`; hạn chế hiện tại là chữ viết tắt như `TS.`, `v.v.` và một số cách viết số thập phân có thể bị nhận nhầm là ranh giới câu.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử separator theo thứ tự từ ranh giới lớn đến nhỏ; mảnh còn quá dài được đệ quy với các separator còn lại, sau đó các mảnh nhỏ liền kề được gom lên tới sát `chunk_size`. Ba base case là text rỗng trả `[]`, text không vượt `chunk_size` trả một chunk, và khi hết separator hoặc gặp separator `""` thì cắt cứng theo `chunk_size` để luôn kết thúc an toàn.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` chuyển từng `Document` thành đúng một record in-memory gồm ID duy nhất, nội dung, bản sao metadata và vector embedding; hàm không tự chia chunk. Với ID chunk dạng `file#0`, metadata `doc_id` vẫn trỏ về `file` gốc; `search` embedding câu hỏi, tính dot product với từng vector đã chuẩn hóa, sắp xếp score giảm dần và trả tối đa `top_k` kết quả mà không đưa embedding vào output.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc record theo tất cả cặp key-value trong metadata trước, sau đó mới tính similarity trên tập ứng viên còn lại. `delete_document` tìm mọi record có `metadata['doc_id']` trùng ID tài liệu, xóa toàn bộ các chunk tương ứng và trả `True`; nếu không tìm thấy thì trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `answer` lấy top-k chunk từ `EmbeddingStore`, đánh số `[1]`, `[2]`, `[3]`, gắn nguồn từ metadata và nối chúng thành khối `Context` trước khi chèn câu hỏi. Prompt yêu cầu mô hình chỉ dùng context, trích dẫn số chunk và nói rõ không tìm thấy nếu thiếu dữ liệu; nếu store rỗng, agent trả thông báo ngay mà không gọi `llm_fn`.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.9.13, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\\VinAI\\Lab\\Day7\\K4-DAY07-DuongVanThanh-2A202602368
plugins: anyio-4.12.1
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================= 42 passed in 0.11s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

> Kết quả trên được lấy trực tiếp từ lệnh `pytest tests/ -v` trong môi trường Python 3.9.13.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có thể yêu cầu hoàn tiền nếu kiện hàng không đến. | Khách hàng được quyền lấy lại tiền khi đơn hàng không được giao. | Cao | 0,5569 | Đúng |
| 2 | Người bán phải phản hồi yêu cầu đổi trả trong ba ngày làm việc. | Mô hình embedding biến văn bản thành vector số. | Thấp | 0,0828 | Đúng |
| 3 | Không thể hủy đơn sau khi người bán đã giao hàng. | Nếu món hàng đã được gửi đi thì yêu cầu hủy sẽ không còn khả dụng. | Cao | 0,5469 | Đúng |
| 4 | Top Rated Seller được bảo vệ khi đáp ứng các tiêu chí của eBay. | Dự báo thời tiết ngày mai có mưa lớn. | Thấp | -0,1232 | Đúng |
| 5 | Người mua phải báo chưa nhận được hàng trong vòng 30 ngày. | Khách hàng cần thông báo món hàng không đến trước khi hết hạn bảo vệ. | Cao | 0,4745 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 bất ngờ nhất vì hai câu gần như cùng nghiệp vụ nhưng score chỉ đạt 0,4745, thấp hơn hai cặp paraphrase còn lại. Điều này cho thấy embedding nắm được ý nghĩa tổng quát nhưng độ gần còn chịu ảnh hưởng bởi mức độ cụ thể của câu: một câu nêu rõ “30 ngày”, câu kia chỉ nói “trước khi hết hạn”, nên không nên dùng một ngưỡng cosine cố định như bằng chứng duy nhất về tính liên quan.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-3 Chunk truy xuất được (score) | Điểm | Có chunk chứa đáp án? | Khả năng trả lời từ context |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Sau khi yêu cầu hủy được gửi, bên còn lại có bao lâu để phản hồi? | `buyer-returns#3` (0,5152); `buyer-cancel#2` (0,4990); `item-not-received#6` (0,4602) | 0/2 | Không — marker nằm ở `buyer-cancel#1` | Không đủ để trả đúng “3 ngày theo lịch”; dễ nhầm với 3 ngày làm việc. |
| 2 | Người mua phải báo chưa nhận được hàng trong thời hạn bao lâu để đủ điều kiện bảo vệ? | `item-not-received#2` (0,6614); `seller-protections#4` (0,6109); `seller-step-in#6` (0,6046) | 2/2 | Có — top-1 | Đủ căn cứ trả lời 30 ngày theo lịch sau ngày giao dự kiến. |
| 3 | Điều kiện nào để Top Rated Seller được hưởng bảo vệ của eBay? | `seller-protections#1` (0,8365); `#17` (0,7180); `#0` (0,7167) | 2/2 | Có — top-1 | Đủ căn cứ về cấp seller, khu vực, metrics, eBay.com và trả hàng ≥30 ngày. |
| 4 | Người mua thực hiện các bước nào để báo một món hàng chưa đến? | `item-not-received#2` (0,6682); `buyer-returns#3` (0,6186); `buyer-returns#0` (0,6095) | 0/2 | Không — marker nằm ở `item-not-received#3` | Không đủ để liệt kê chính xác toàn bộ thao tác. |
| 5 | Người bán có thể chọn những thời hạn và hình thức trả hàng nào? | `seller-return#0` (0,6267); `seller-return#1` (0,6180); `seller-protections#14` (0,5635) | 1/2 | Có — top-2 | Đủ căn cứ về lựa chọn 30/60 ngày và ngoại lệ 14 ngày. |

> Cột cuối đánh giá khả năng trả lời dựa trên marker có thật trong context top-3; chưa gọi LLM bên ngoài. Vì vậy đây là điểm retrieval/content-grounding, không được trình bày như một phép chấm chất lượng sinh câu của mô hình.

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 3 / 5 — document-level là 5/5 nhưng answer-bearing chunk chỉ đạt 3/5, tương ứng 5/10 điểm theo rank.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Tôi học được rằng không nên đánh giá retrieval chỉ bằng việc đúng `doc_id`, vì một tài liệu dài có thể chiếm cả top-3 nhưng các chunk đều không chứa đáp án. So sánh với nhánh Recursive của Nguyễn Viết Đức cũng cho thấy giữ ranh giới đoạn và gom các mảnh nhỏ có thể hiệu quả hơn việc lặp một heading chung; lần sau tôi sẽ thêm heading cấp section và overlap nhỏ trước khi rerank.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 5 / 10 |
| **Tổng phần cá nhân** | **55 / 60** |
