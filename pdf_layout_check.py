"""
PDF排版质量自动检测脚本
检测：文字重叠、溢出页面边界、行间距异常
用法：python pdf_layout_check.py <pdf_path>
"""
import pymupdf
import sys
import os


def check_pdf_layout(pdf_path):
    """检测PDF排版问题，返回问题列表"""
    issues = []
    doc = pymupdf.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_rect = page.rect  # 页面边界
        blocks = page.get_text("dict")["blocks"]

        # 收集所有文本行的bbox
        line_bboxes = []
        for block in blocks:
            if block["type"] != 0:  # 只检查文本块
                continue
            for line in block["lines"]:
                bbox = line["bbox"]  # (x0, y0, x1, y1)
                text = "".join(span["text"] for span in line["spans"])
                if text.strip():
                    line_bboxes.append({
                        "bbox": bbox,
                        "text": text[:30],
                        "page": page_num + 1
                    })

        # 检测1：文字溢出页面边界
        margin = 10  # 允许10pt误差
        for item in line_bboxes:
            b = item["bbox"]
            if b[0] < page_rect.x0 - margin:
                issues.append(f"P{item['page']}: 文字左溢出 - '{item['text']}'")
            if b[2] > page_rect.x1 + margin:
                issues.append(f"P{item['page']}: 文字右溢出 - '{item['text']}'")
            if b[1] < page_rect.y0 - margin:
                issues.append(f"P{item['page']}: 文字上溢出 - '{item['text']}'")
            if b[3] > page_rect.y1 + margin:
                issues.append(f"P{item['page']}: 文字下溢出 - '{item['text']}'")


        # 检测2：文字块重叠（同一页内两个行的bbox有交集）
        for i in range(len(line_bboxes)):
            for j in range(i + 1, len(line_bboxes)):
                b1 = line_bboxes[i]["bbox"]
                b2 = line_bboxes[j]["bbox"]
                # 计算交集
                overlap_x = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
                overlap_y = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
                if overlap_x > 2 and overlap_y > 2:
                    overlap_area = overlap_x * overlap_y
                    # 忽略很小的重叠（<5pt^2）
                    if overlap_area > 5:
                        issues.append(
                            f"P{line_bboxes[i]['page']}: 文字重叠 - "
                            f"'{line_bboxes[i]['text']}' 与 "
                            f"'{line_bboxes[j]['text']}'"
                        )

        # 检测3：行间距异常（相邻行间距<1pt，可能挤压）
        # 排除代码块和表格单元格
        sorted_lines = sorted(line_bboxes, key=lambda x: (x["bbox"][1], x["bbox"][0]))
        for i in range(len(sorted_lines) - 1):
            b1 = sorted_lines[i]["bbox"]
            b2 = sorted_lines[i + 1]["bbox"]
            # 跳过代码块内容
            if sorted_lines[i]["text"].strip() in ('v', '->', ''):
                continue
            if sorted_lines[i]["text"].startswith('  '):
                continue
            # 只检查垂直方向确实相邻的行（y坐标差<行高2倍）
            line_height = b1[3] - b1[1]
            y_dist = b2[1] - b1[1]
            if y_dist > line_height * 2.5 or y_dist < line_height * 0.3:
                continue  # 不是真正的相邻行（跨行或同行不同列）
            # 计算间距
            gap = b2[1] - b1[3]
            if gap < -2:  # 负间距>2pt表示真正的重叠
                issues.append(
                    f"P{sorted_lines[i]['page']}: 行间距异常({gap:.1f}pt) - "
                    f"'{sorted_lines[i]['text']}'"
                )

    doc.close()
    return issues


def main():
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # 默认路径
        pdf_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'report_202606.pdf'
        )

    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Checking: {pdf_path}")
    issues = check_pdf_layout(pdf_path)

    if not issues:
        print("PASS: No layout issues detected.")
    else:
        print(f"ISSUES FOUND: {len(issues)}")
        for issue in issues[:20]:  # 只显示前20个
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
        sys.exit(1)


if __name__ == '__main__':
    main()
