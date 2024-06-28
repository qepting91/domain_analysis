import sys
import os
import urllib.request
import requests
from bs4 import BeautifulSoup
import whois
import dns.resolver
import dns.reversename
import pygeoip
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import inch
import time
from urllib.parse import urlparse

def ensure_geolite_data():
    geolite_path = 'GeoLiteCity.dat'
    if not os.path.exists(geolite_path):
        print("Downloading GeoLiteCity.dat...")
        url = "https://github.com/mbcc2006/GeoLiteCity-data/raw/master/GeoLiteCity.dat"
        try:
            urllib.request.urlretrieve(url, geolite_path)
            print("Download complete.")
        except Exception as e:
            print(f"Error downloading GeoLiteCity.dat: {e}")
            sys.exit(1)
    return geolite_path

def fetch_web_content(url):
    response = requests.get(url)
    return response.text

def parse_html_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    links = [link['href'] for link in soup.find_all('a', href=True)]
    text_content = soup.get_text()
    return links, text_content

def get_domain_info(domain):
    retries = 3
    for _ in range(retries):
        try:
            domain_info = whois.whois(domain)
            return domain_info
        except Exception as e:
            print(f"Error: {e}. Retrying...")
            time.sleep(5)
    return None

def get_dns_info(domain):
    try:
        result = dns.resolver.resolve(domain, 'A')
        return [ip.to_text() for ip in result]
    except Exception as e:
        print(f"DNS resolution error: {e}")
        return []

def get_mx_info(domain):
    try:
        result = dns.resolver.resolve(domain, 'MX')
        return [mx.to_text() for mx in result]
    except Exception as e:
        print(f"DNS MX resolution error: {e}")
        return []

def reverse_dns_lookup(ip):
    try:
        addr = dns.reversename.from_address(ip)
        result = dns.resolver.resolve(addr, 'PTR')
        return [ptr.to_text() for ptr in result]
    except Exception as e:
        print(f"Reverse DNS lookup error: {e}")
        return []

def get_ip_geolocation(ip):
    try:
        geolite_path = ensure_geolite_data()
        geo = pygeoip.GeoIP(geolite_path)
        return geo.record_by_addr(ip)
    except Exception as e:
        print(f"Geolocation error: {e}")
        return {}

def create_pdf_report(url, content, links, text_content, domain_info, dns_info, mx_info, reverse_dns, geo_info):
    pdf_file = 'report.pdf'
    doc = SimpleDocTemplate(pdf_file, pagesize=letter)
    styles = getSampleStyleSheet()
    flowables = []

    styleH = ParagraphStyle(
        name='Heading1',
        fontSize=14,
        leading=16,
        alignment=1,
        spaceAfter=12,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    )

    styleB = styles['BodyText']
    styleB.fontSize = 10
    styleB.leading = 12

    title = Paragraph(f"URL Report for {url}", styleH)
    flowables.append(title)
    flowables.append(Spacer(1, 12))

    toc_title = Paragraph("Table of Contents", styleH)
    flowables.append(toc_title)
    flowables.append(Spacer(1, 12))

    toc = [
        ["Web Content"],
        ["Extracted Links"],
        ["Domain Information"],
        ["DNS Information"],
        ["MX Information"],
        ["Reverse DNS Information"],
        ["Geolocation Information"]
    ]

    toc_table = Table(toc, colWidths=[6*inch])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    flowables.append(toc_table)
    flowables.append(PageBreak())

    def add_header(text):
        header = Paragraph(text, styleH)
        flowables.append(header)
        flowables.append(Spacer(1, 6))

    def add_paragraph(text):
        para = Paragraph(text, styleB)
        flowables.append(para)
        flowables.append(Spacer(1, 12))

    def add_table(data, col_widths):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        flowables.append(table)
        flowables.append(Spacer(1, 12))

    add_header("Web Content")
    add_paragraph(text_content[:3000])
    flowables.append(PageBreak())

    add_header("Extracted Links")
    if links:
        links_table = [[Paragraph(link, styleB)] for link in links]
        add_table(links_table, [6*inch])
    else:
        add_paragraph("No extracted links available.")
    flowables.append(PageBreak())

    add_header("Domain Information")
    if domain_info:
        domain_table = [[Paragraph(f"{key}: {value}", styleB)] for key, value in domain_info.items()]
        add_table(domain_table, [6*inch])
    else:
        add_paragraph("Failed to retrieve domain information.")
    flowables.append(PageBreak())

    add_header("DNS Information")
    if dns_info:
        dns_table = [[Paragraph(dns, styleB)] for dns in dns_info]
        add_table(dns_table, [6*inch])
    else:
        add_paragraph("No DNS information available.")
    flowables.append(PageBreak())

    add_header("MX Information")
    if mx_info:
        mx_table = [[Paragraph(mx, styleB)] for mx in mx_info]
        add_table(mx_table, [6*inch])
    else:
        add_paragraph("No MX information available.")
    flowables.append(PageBreak())

    add_header("Reverse DNS Information")
    if reverse_dns:
        reverse_dns_table = [[Paragraph(reverse_dns, styleB)] for reverse_dns in reverse_dns]
        add_table(reverse_dns_table, [6*inch])
    else:
        add_paragraph("No reverse DNS information available.")
    flowables.append(PageBreak())

    add_header("Geolocation Information")
    if geo_info:
        geo_table = [[Paragraph(f"{key}: {value}", styleB)] for key, value in geo_info.items()]
        add_table(geo_table, [6*inch])
    else:
        add_paragraph("No geolocation information available.")

    doc.build(flowables)
    return pdf_file

def format_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url

def main():
    ensure_geolite_data()

    if len(sys.argv) != 2:
        print("Usage: python domain_analysis.py <url>")
        sys.exit(1)

    url = format_url(sys.argv[1])
    domain = urlparse(url).netloc

    print(f"Analyzing domain: {domain}")

    try:
        web_content = fetch_web_content(url)
        links, text_content = parse_html_content(web_content)
        domain_info = get_domain_info(domain)
        dns_info = get_dns_info(domain)
        mx_info = get_mx_info(domain)
        reverse_dns = reverse_dns_lookup(dns_info[0]) if dns_info else []
        geo_info = get_ip_geolocation(dns_info[0]) if dns_info else {}

        pdf_file = create_pdf_report(url, web_content, links, text_content, domain_info, dns_info, mx_info, reverse_dns, geo_info)
        print(f"PDF report generated: {pdf_file}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching web content: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
