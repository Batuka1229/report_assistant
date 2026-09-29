"""Streamlit entry point for the Report AI Assistant."""

from __future__ import annotations

import logging
from hashlib import sha256

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from ai.analysis_runner import aggregate_insights, run_ai_analysis
from ai.model_router import ModelRouter
from charts.chart_generator import create_charts
from config.settings import MAX_UPLOAD_MB
from data.analyzer import DataAnalyzer
from data.loader import DataLoader
from data.profiler import DataProfiler
from data.validator import DataValidator
from models.schemas import ReportContent
from reports.excel_generator import generate_excel_report
from reports.pdf_generator import generate_pdf_report
from reports.word_generator import generate_word_report
from utils.formatter import build_report_content
from utils.logger import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
st.set_page_config(page_title="Report AI Assistant", page_icon="📊", layout="wide")
st.title("Report AI Assistant")
st.caption("Pandas + NumPy тооцоолно · AI тайлбарлана · Тайлан нэгтгэнэ")

loader = DataLoader()
router = ModelRouter()
with st.sidebar:
    st.header("Report AI Assistant")
    st.subheader("1. Файл оруулах")
    uploaded_file = st.file_uploader(
        "Excel / CSV файл оруулах",
        type=["xlsx", "xls", "csv"],
        help=f"Файлын дээд хэмжээ: {MAX_UPLOAD_MB} MB. Файл серверт хадгалагдахгүй.",
    )

    options: dict[str, bool] = {}
    st.subheader("3. Шинжилгээний сонголт")
    for key, label in [
        ("DATA_ANALYSIS", "Өгөгдлийн хураангуй"),
        ("KPI_ANALYSIS", "KPI шинжилгээ"),
        ("TREND_ANALYSIS", "Хугацааны шинжилгээ"),
        ("CATEGORY_COMPARISON", "Ангиллын харьцуулалт"),
        ("ANOMALY_ANALYSIS", "Онцгой утгын шинжилгээ"),
        ("CORRELATION_ANALYSIS", "Хамаарлын шинжилгээ"),
        ("AI_INSIGHTS", "AI insights"),
        ("EXECUTIVE_SUMMARY", "Удирдлагын хураангуй"),
    ]:
        options[key] = st.checkbox(label, value=key in {"DATA_ANALYSIS", "KPI_ANALYSIS", "AI_INSIGHTS"})

    st.subheader("4. AI загвар")
    providers = router.available_providers()
    selected_provider = st.selectbox(
        "Нийлүүлэгч / загвар",
        providers or ["AI тохируулаагүй"],
        disabled=not providers,
        help="Нийлүүлэгчийг .env файл дахь OpenAI-compatible endpoint-оор тохируулна.",
    )
    st.selectbox("Тайлангийн хэл", ["Монгол"], disabled=True)
    st.subheader("6. Тайлангийн формат")
    formats = {
        "PDF": st.checkbox("PDF", value=True),
        "Word": st.checkbox("Word (DOCX)", value=True),
        "Excel": st.checkbox("Excel (XLSX)", value=True),
    }

if uploaded_file is None:
    st.info("Эхлэхийн тулд Excel эсвэл CSV файл оруулна уу.")
    st.stop()

if uploaded_file.size > MAX_UPLOAD_MB * 1024 * 1024:
    st.error(f"Файлын хэмжээ {MAX_UPLOAD_MB} MB хязгаараас хэтэрлээ.")
    st.stop()

file_bytes = uploaded_file.getvalue()
file_id = sha256(file_bytes).hexdigest()
try:
    sheet_names = loader.get_sheets(file_bytes, uploaded_file.name)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
if not sheet_names:
    st.error("Excel файлд унших боломжтой хуудас алга.")
    st.stop()

with st.sidebar:
    st.subheader("2. Хуудас сонгох")
    selected_sheet = st.selectbox("Sheet", sheet_names, key=f"sheet-{file_id}")
    st.caption("Хуудаснууд: " + ", ".join(sheet_names))

try:
    df = loader.load_sheet(file_bytes, selected_sheet, uploaded_file.name)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

validation = DataValidator().validate(df)
profile = DataProfiler().profile(df)
analysis = DataAnalyzer(df, profile).generate_analysis()

st.subheader("Өгөгдлийн тойм")
st.caption(f"Файл: {uploaded_file.name} · Хуудас: {selected_sheet} · {len(sheet_names)} sheet")
overview = st.columns(4)
overview[0].metric("Мөр", f"{len(df):,}")
overview[1].metric("Багана", f"{len(df.columns):,}")
overview[2].metric("Дутуу утга", f"{analysis['data_quality']['total_missing_values']:,}")
overview[3].metric("Давхардсан мөр", f"{validation['duplicate_rows']:,}")

for error in validation["errors"]:
    st.error(error)
for warning in validation["warnings"]:
    st.warning(warning)
if not validation["is_valid"]:
    st.stop()

with st.expander("Профайл болон эх өгөгдлийн урьдчилсан харагдац", expanded=False):
    st.write({
        "Тоо": profile["numeric_columns"],
        "Огноо": profile["date_columns"],
        "Ангилал": profile["categorical_columns"],
        "Текст": profile["text_columns"],
        "Таних дугаар": profile["id_columns"],
    })
    st.dataframe(df.head(100), use_container_width=True)

st.subheader("KPI самбар")
if analysis["kpis"]:
    kpi_columns = st.columns(min(len(analysis["kpis"]), 4))
    for index, kpi in enumerate(analysis["kpis"]):
        kpi_columns[index % len(kpi_columns)].metric(
            kpi["column"], f"{kpi['sum']:,.2f}" if kpi["sum"] is not None else "—",
            help=f"Дундаж: {kpi['average']} · Бага: {kpi['minimum']} · Их: {kpi['maximum']}",
        )
    st.dataframe(
        [
            {
                "Үзүүлэлт": item["column"],
                "Нийт": item["sum"],
                "Дундаж": item["average"],
                "Хамгийн бага": item["minimum"],
                "Хамгийн их": item["maximum"],
            }
            for item in analysis["kpis"]
        ],
        hide_index=True,
        use_container_width=True,
    )
else:
    st.caption("KPI-д тохирох тоон багана илрээгүй.")

st.subheader("График")
charts = create_charts(df, profile)
if charts:
    chart_columns = st.columns(2)
    for index, (title, figure) in enumerate(charts):
        with chart_columns[index % 2]:
            st.plotly_chart(figure, use_container_width=True, key=f"chart-{file_id}-{index}")
else:
    st.caption("График үүсгэхэд тохирох өгөгдөл илрээгүй.")

generate = st.button("Тайлан үүсгэх", type="primary", use_container_width=True)
result_key = f"{file_id}:{selected_sheet}"
if generate:
    ai_tasks = []
    for option, task in [
        ("DATA_ANALYSIS", "DATA_ANALYSIS"),
        ("KPI_ANALYSIS", "KPI_ANALYSIS"),
        ("TREND_ANALYSIS", "TREND_ANALYSIS"),
        ("CATEGORY_COMPARISON", "CATEGORY_COMPARISON"),
        ("ANOMALY_ANALYSIS", "ANOMALY_ANALYSIS"),
        ("CORRELATION_ANALYSIS", "CORRELATION_ANALYSIS"),
        ("EXECUTIVE_SUMMARY", "EXECUTIVE_SUMMARY"),
    ]:
        if options[option]:
            ai_tasks.append(task)
    if options["AI_INSIGHTS"] and "DATA_ANALYSIS" not in ai_tasks:
        ai_tasks.append("DATA_ANALYSIS")

    ai_results = {}
    insights = {"summary": [], "insights": [], "recommendations": []}
    selected_router = ModelRouter(selected_provider) if providers else None
    if ai_tasks and not providers:
        st.warning("AI загвар тохируулаагүй тул AI хэсгийг алгасаж, тооцоолсон үр дүнгээр тайлан үүсгэлээ.")
    elif ai_tasks:
        try:
            assert selected_router is not None
            for task in list(dict.fromkeys(ai_tasks)):
                try:
                    ai_results.update(run_ai_analysis(analysis, [task], selected_router))
                except (RuntimeError, ValueError) as exc:
                    logger.warning("AI task %s failed: %s", task, exc)
                    st.warning(f"{task} AI шинжилгээ амжилтгүй боллоо; бусад үр дүнг үргэлжлүүлэн боловсруулна.")
            insights = aggregate_insights(ai_results)
        except (RuntimeError, ValueError) as exc:
            logger.warning("AI analysis failed: %s", exc)
            st.warning(f"AI шинжилгээ амжилтгүй боллоо. Тооцоолсон үр дүнгээр тайлан үүсгэлээ. ({exc})")

    report_content: ReportContent | None = None
    if selected_router is not None:
        try:
            from ai.report_writer import AIReportWriter

            report_content = AIReportWriter(selected_router.get_model("REPORT_WRITING")).write(analysis, insights)
        except (RuntimeError, ValueError) as exc:
            logger.warning("AI report writing failed: %s", exc)
            st.warning(f"AI тайлан бичигч ашиглагдсангүй; загвар тайлан харуулна. ({exc})")

    report_content = build_report_content(analysis, insights, report_content)
    report_files: dict[str, bytes] = {}
    try:
        if formats["PDF"]:
            report_files["PDF"] = generate_pdf_report(analysis, insights, report_content, df, profile)
        if formats["Word"]:
            report_files["DOCX"] = generate_word_report(analysis, insights, report_content, df, profile)
        if formats["Excel"]:
            report_files["XLSX"] = generate_excel_report(analysis, insights, report_content)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.exception("Report generation failed.")
        st.error(f"Тайлан үүсгэхэд алдаа гарлаа: {exc}")
    else:
        st.session_state[result_key] = {
            "analysis": analysis,
            "insights": insights,
            "report": report_content,
            "files": report_files,
        }

saved = st.session_state.get(result_key)
if saved:
    st.subheader("AI Insights")
    if saved["insights"]["summary"]:
        for item in saved["insights"]["summary"]:
            st.write(f"- {item}")
    for insight in saved["insights"]["insights"]:
        st.markdown(f"**{insight['title']}** — {insight['description']}")
    for recommendation in saved["insights"]["recommendations"]:
        st.write(f"Санал: {recommendation}")
    st.subheader("Тайлангийн урьдчилсан харагдац")
    report_preview = saved["report"]
    if report_preview:
        st.markdown(f"### {report_preview.title}")
        for item in report_preview.executive_summary:
            st.write(f"- {item}")
        for section in report_preview.sections:
            with st.expander(section.title):
                st.write(section.content)
        for item in report_preview.conclusion:
            st.write(item)
    else:
        st.info("AI тайлан үүсгээгүй үед тооцоолсон шинжилгээг тайлангийн файлд оруулав.")
    st.subheader("Татаж авах")
    download_columns = st.columns(3)
    download_config = {
        "PDF": ("report.pdf", "application/pdf"),
        "DOCX": ("report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "XLSX": ("report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    }
    for index, (kind, payload) in enumerate(saved["files"].items()):
        filename, mime = download_config[kind]
        download_columns[index % len(download_columns)].download_button(
            f"{kind} татах", payload, file_name=filename, mime=mime, key=f"download-{result_key}-{kind}"
        )