import polars as pl
import pathlib
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import date
# from emailer import send_email
import logging

BASE_DIR = pathlib.Path(__file__).resolve().parent
SALES_FOLDER = BASE_DIR / 'sales'
OUTPUT_FOLDER = BASE_DIR / 'output'
REPORT_TO = 'boss@example.com'

log = logging.getLogger('report_robot')


def main():
    log.info('Report robot started')

    # Read every Excel file in the sales folder and join them
    tables = []
    for path in sorted(SALES_FOLDER.glob('*.xlsx')):
        if path.name.startswith('~$'):
            continue
        log.info(f'Reading {path.name}')
        table = pl.read_excel(path)
        tables.append(table)
    if not tables:
        raise FileNotFoundError(f'No Excel files found in {SALES_FOLDER}')
    all_tables = pl.concat(tables)
    log.info(f'Read {len(all_tables)} rows')

    # Revenue and totals
    all_tables = all_tables.with_columns(Revenue=pl.col('Units') * pl.col('Unit Price'))
    region_totals = all_tables.group_by('Region').agg(pl.col('Units', 'Revenue').sum())
    region_totals = region_totals.sort('Revenue', descending=True)
    product_totals = all_tables.group_by('Product').agg(pl.col('Units', 'Revenue').sum())
    product_totals = product_totals.sort('Revenue', descending=True)

    # Chart
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    chart_path = OUTPUT_FOLDER / 'revenue_by_region.png'
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(region_totals['Region'], region_totals['Revenue'], color='#2563eb')
    ax.bar_label(bars, fmt='{:,.0f}')
    ax.set_title('Revenue by region')
    ax.set_ylabel('Revenue')
    ax.yaxis.set_major_formatter('{x:,.0f}')
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(chart_path, dpi=200)
    plt.close(fig)

    # PDF
    start = all_tables['Date'].min()
    end = all_tables['Date'].max()
    title = f'Sales Report: {start:%d %b} to {end:%d %b %Y}'
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', style='B', size=20)
    pdf.cell(text=title, new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=11)
    pdf.cell(text=f'Created on {date.today():%d %b %Y} by the report robot.')
    pdf.ln(12)

    pdf.set_font('Helvetica', style='B', size=14)
    pdf.cell(text='Revenue by region', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    pdf.set_font('Helvetica', size=11)
    with pdf.table(text_align=('LEFT', 'RIGHT', 'RIGHT')) as pdf_table:
        header = pdf_table.row()
        for name in region_totals.columns:
            header.cell(name)
        for name, units, revenue in region_totals.iter_rows():
            row = pdf_table.row()
            row.cell(str(name))
            row.cell(f'{units:,}')
            row.cell(f'{revenue:,.2f}')
    pdf.ln(4)
    pdf.image(str(chart_path), w=pdf.epw)
    pdf.ln(6)

    pdf.set_font('Helvetica', style='B', size=14)
    pdf.cell(text='Revenue by product', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    pdf.set_font('Helvetica', size=11)
    with pdf.table(text_align=('LEFT', 'RIGHT', 'RIGHT')) as pdf_table:
        header = pdf_table.row()
        for name in product_totals.columns:
            header.cell(name)
        for name, units, revenue in product_totals.iter_rows():
            row = pdf_table.row()
            row.cell(str(name))
            row.cell(f'{units:,}')
            row.cell(f'{revenue:,.2f}')

    pdf_path = OUTPUT_FOLDER / f'sales_report_{date.today()}.pdf'
    pdf.output(str(pdf_path))
    log.info(f'Report saved to {pdf_path}')

    # Email
    # best = region_totals.row(0, named=True)
    # total = all_tables['Revenue'].sum()
    # body = (
    #     f'Hi,\n\n{title} is attached as a PDF.\n\n'
    #     f'Total revenue: {total:,.2f}\n'
    #     f"Best region: {best['Region']} ({best['Revenue']:,.2f})\n\n"
    #     'This email was sent by the report robot.'
    # )
    # # send_email(REPORT_TO, title, body, attachment=pdf_path)
    # log.info(f'Report sent to {REPORT_TO}')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(BASE_DIR / 'robot.log'), logging.StreamHandler()],
    )
    try:
        main()
    except Exception:
        log.exception('The report robot failed')
        raise
