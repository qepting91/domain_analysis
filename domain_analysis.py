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
from urllib.parse import urlparse, urljoin
from wayback import WaybackClient
import json
import subprocess

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
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        print(f"Successfully fetched content from {url}")
        print(f"Response status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching content from {url}: {e}")
        return None

def parse_html_content(html):
    if not html:
        print("No HTML content to parse")
        return [], ""
    
    soup = BeautifulSoup(html, 'html.parser')
    links = [link['href'] for link in soup.find_all('a', href=True)]
    text_content = soup.get_text()
    
    print(f"Number of links extracted: {len(links)}")
    print(f"Length of text content: {len(text_content)}")
    
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

def run_oxdork(domain):
    results = []
    with open('queries.txt', 'r') as f:
        queries = f.readlines()
    
    for query in queries:
        formatted_query = query.strip().format(domain=domain)
        try:
            result = subprocess.run(['oxdork', formatted_query, '-c', '20'], capture_output=True, text=True, timeout=70)
            if result.returncode == 0:
                results.append(f"Query: {formatted_query}\n{result.stdout}")
            else:
                results.append(f"Error running query '{formatted_query}': {result.stderr}")
        except subprocess.TimeoutExpired:
            results.append(f"Timeout expired while running query '{formatted_query}'")
        except Exception as e:
            results.append(f"Exception while running query '{formatted_query}': {e}")
    
    return results

def fetch_wayback_snapshots(domain):
    client = WaybackClient()
    snapshots = client.search(domain)
    snapshots_list = []
    for snapshot in snapshots:
        snapshots_list.append((snapshot.url, snapshot.timestamp))
    return snapshots_list

def create_pdf_report(url, content, links, text_content, domain_info, dns_info, mx_info, reverse_dns, geo_info, oxdork_result, wayback_snapshots):
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

    styleB = ParagraphStyle(
        'BodyText',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceBefore=6,
        spaceAfter=6
    )

    info_text = {
        "Web Content": "This section displays the first 6000 characters of the web page content.",
        "Extracted Links": "These are all the hyperlinks found on the analyzed web page.",
        "Domain Information": "This information is retrieved from the WHOIS database for the domain.",
        "DNS Information": "These are the A records for the domain, showing its IP addresses.",
        "MX Information": "These are the mail exchanger records for the domain.",
        "Reverse DNS Information": "This shows the domain names associated with the IP addresses.",
        "Geolocation Information": "This provides geographical information based on the IP address.",
        "Oxdork Results": "Results from the oxdork tool.",
        "Wayback Machine Snapshots": "These are historical snapshots of the website."
    }

    osint_value = {
        "Web Content": """
        <b>Description</b>: Provides insight into the website's purpose and content.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Purpose Identification</b>: The primary content on a website can reveal its purpose, whether it's an e-commerce site, a personal blog, a corporate page, or a phishing site.</li>
            <li><b>Sentiment Analysis</b>: Analyzing the tone and sentiment of the content can provide insights into the site's intentions or biases.</li>
            <li><b>Keyword Extraction</b>: Extracting key phrases and words can help identify the main topics and areas of focus, which is useful for further keyword-based searches.</li>
            <li><b>Pivot for Attribution</b>: By identifying specific jargon, themes, or repeated phrases, analysts can link the site to other similar sites or content, potentially leading to the identification of common authors or organizations behind multiple sites.</li>
        </ul>
        """,
        "Extracted Links": """
        <b>Description</b>: Reveals connections to other websites and potential infrastructure.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Network Mapping</b>: Extracting all hyperlinks from a site can help map out its network of connections, revealing related sites, partners, or affiliates.</li>
            <li><b>Hidden Relationships</b>: Discovering links to seemingly unrelated sites can expose hidden relationships or common ownership.</li>
            <li><b>Tracking Infrastructure</b>: Links to external resources (images, scripts, CSS) can identify third-party services in use, providing clues to the website's infrastructure.</li>
            <li><b>Pivot for Attribution</b>: Shared link patterns can indicate a common webmaster or organization, aiding in connecting multiple sites to a single entity.</li>
        </ul>
        """,
        "Domain Information": """
        <b>Description</b>: Offers details about domain ownership and registration.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>WHOIS Lookup</b>: Provides registrant information, including name, organization, address, and contact details. This can be instrumental in identifying the owner.</li>
            <li><b>Domain History</b>: Tools like DomainTools can provide historical data on domain ownership, helping to track changes over time.</li>
            <li><b>Registration Patterns</b>: Analyzing the registration patterns (e.g., registrar, registration date, expiry date) can provide insights into the domain's lifecycle and purpose.</li>
            <li><b>Pivot for Attribution</b>: Cross-referencing WHOIS data with other domains can reveal a common owner or organizational entity, aiding in building a network of connected domains.</li>
        </ul>
        """,
        "DNS Information": """
        <b>Description</b>: Identifies the hosting infrastructure and potential related domains.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>DNS Records</b>: Examining records such as A, MX, CNAME, NS, and TXT can provide insights into the server locations, email servers, and service configurations.</li>
            <li><b>Reverse DNS</b>: Performing reverse DNS lookups can identify other domains hosted on the same IP address, which can indicate related or owned domains.</li>
            <li><b>Subdomains</b>: Identifying subdomains can uncover additional services or sections of a website that are not immediately visible.</li>
            <li><b>Pivot for Attribution</b>: Common DNS records or shared hosting environments can link multiple domains to the same owner or infrastructure, providing a broader picture of their online presence.</li>
        </ul>
        """,
        "MX Information": """
        <b>Description</b>: Indicates email providers and potential communication channels.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Mail Servers</b>: MX records reveal the email servers used by a domain, which can indicate the email provider and security measures in place.</li>
            <li><b>Email Patterns</b>: Understanding the email infrastructure can provide insights into communication habits and potential vulnerabilities.</li>
            <li><b>Pivot for Attribution</b>: Shared MX records across domains can suggest common ownership or administrative control, aiding in mapping an organization's email infrastructure.</li>
        </ul>
        """,
        "Reverse DNS Information": """
        <b>Description</b>: Can reveal hosting patterns and related domains.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>IP to Domain Mapping</b>: Reverse DNS lookups convert IP addresses back to domain names, revealing all domains associated with a given IP.</li>
            <li><b>Shared Hosting Analysis</b>: Identifying multiple domains on the same server can suggest common ownership or a shared hosting service.</li>
            <li><b>Pivot for Attribution</b>: Patterns in reverse DNS results can link multiple domains to a single hosting provider or infrastructure, providing clues to the network behind the domains.</li>
        </ul>
        """,
        "Geolocation Information": """
        <b>Description</b>: Helps in identifying the physical location of the server.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Server Location</b>: Tools like IP geolocation can pinpoint the physical location of the server, which can indicate the jurisdiction and potential regulatory environment.</li>
            <li><b>Regional Analysis</b>: Understanding the server's location can provide context about the site's target audience and operational region.</li>
            <li><b>Pivot for Attribution</b>: Correlating server locations with domain ownership and content can help attribute websites to specific regions or organizations, narrowing down the potential operators.</li>
        </ul>
        """,
        "Oxdork Results": """
        <b>Description</b>: Identifies vulnerabilities and information based on Google dorking.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Advanced Search Techniques</b>: Using Google dorks to uncover sensitive information, such as exposed directories, login pages, and configuration files.</li>
            <li><b>Vulnerability Detection</b>: Identifying misconfigurations, outdated software, and other security vulnerabilities through targeted search queries.</li>
            <li><b>Pivot for Attribution</b>: Discovering unique identifiers or errors across multiple sites can indicate a common development team or webmaster, linking multiple domains together.</li>
        </ul>
        """,
        "Wayback Machine Snapshots": """
        <b>Description</b>: Provides historical data on the website's changes over time.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Website Evolution</b>: Analyzing historical snapshots to understand how a site has evolved, including changes in content, design, and structure.</li>
            <li><b>Incident Analysis</b>: Identifying when significant changes occurred can help correlate with external events or shifts in strategy.</li>
            <li><b>Pivot for Attribution</b>: Consistent patterns or changes across multiple domains in the Wayback Machine can indicate a common webmaster or organizational control, helping to build a timeline of online activity.</li>
        </ul>
        """
    }

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
        ["Geolocation Information"],
        ["Oxdork Results"],
        ["Wayback Machine Snapshots"]
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
        
        if text in info_text:
            info_header = Paragraph("Info:", ParagraphStyle("InfoHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(info_header)
            info = Paragraph(info_text[text], styleB)
            flowables.append(info)
            flowables.append(Spacer(1, 6))
        
        if text in osint_value:
            osint_header = Paragraph("OSINT Value:", ParagraphStyle("OSINTHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(osint_header)
            osint = Paragraph(osint_value[text], styleB)
            flowables.append(osint)
            flowables.append(Spacer(1, 12))

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
    add_paragraph(text_content[:6000])
    flowables.append(PageBreak())

    add_header("Extracted Links")
    if links:
        links_table = [[Paragraph(link, styleB)] for link in links]
        add_table(links_table, [6*inch])
    else:
        add_paragraph("No extracted links available.")
    flowables.append(PageBreak())

    add_header("Domain Information")
    domain_info_text = """
    <b>Domain Information:</b><br/>
    Every domain that's been registered belongs to someone, and by default, that registration information is public.<br/><br/>

    <b>Registrar:</b> The business that you go to purchase a domain. They handle the reservation of the domain as well as the assignment of IP addresses, such as GoDaddy.<br/><br/>

    <b>Registrant:</b> Is the registered holder of a domain. In order for that person to maintain ownership, they have to pay registration fees.<br/><br/>

    To potentially obtain more information you must go to the Registrar's whois. First, identify the Registrar, then google "registrar's name" + "whois". Do not attempt to use the URL provided next to "WHOIS Server".<br/><br/>

    During an investigation it is often useful to see who has previously owned the domain. Or if you are conducting a Person of Interest or domain investigation and followed the steps above and found that everything has been redacted for privacy due to the use of a privacy guard, a historical whois search may provide unredacted information.<br/><br/>

    There are many historical whois tools. The following have been identified as the best that you can scan for free:<br/>
    <a href="https://www.bigdomaindata.com/" color="blue">https://www.bigdomaindata.com/</a><br/>
    <a href="https://www.whoxy.com/whois-history/" color="blue">https://www.whoxy.com/whois-history/</a><br/>
    <a href="https://whois-history.whoisxmlapi.com/" color="blue">https://whois-history.whoisxmlapi.com/</a>
    """
    flowables.append(Paragraph(domain_info_text, styleB))
    flowables.append(Spacer(1, 12))
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
    mx_info_text = """
    An MX record is what allows someone to send emails from a domain.<br/><br/>

    When investigating a domain for suspicious activity, the existence of an MX record is an early warning sign that the domain is enabled to send email which may be used for a variety of email based attacks.
    """
    flowables.append(Paragraph(mx_info_text, styleB))
    flowables.append(Spacer(1, 12))
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
    flowables.append(PageBreak())

    add_header("Oxdork Results")
    if oxdork_result:
        for result in oxdork_result:
            add_paragraph(result)
    else:
        add_paragraph("No Oxdork results available.")
    flowables.append(PageBreak())

    add_header("Wayback Machine Snapshots")
    if wayback_snapshots:
        for url, timestamp in wayback_snapshots:
            link_text = f'<a href="{url}" color="blue">URL: {url}</a> - Timestamp: {timestamp}'
            flowables.append(Paragraph(link_text, styleB))
    else:
        add_paragraph("No Wayback Machine snapshots available.")

    doc.build(flowables)
    return pdf_file

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

    info_text = {
        "Web Content": "This section displays the first 6000 characters of the web page content.",
        "Extracted Links": "These are all the hyperlinks found on the analyzed web page.",
        "Domain Information": "This information is retrieved from the WHOIS database for the domain.",
        "DNS Information": "These are the A records for the domain, showing its IP addresses.",
        "MX Information": "These are the mail exchanger records for the domain.",
        "Reverse DNS Information": "This shows the domain names associated with the IP addresses.",
        "Geolocation Information": "This provides geographical information based on the IP address.",
        "Oxdork Results": "Results from the oxdork tool.",
        "Wayback Machine Snapshots": "These are historical snapshots of the website."
    }

    osint_value = {
        "Web Content": """
        <b>Description</b>: Provides insight into the website's purpose and content.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Purpose Identification</b>: The primary content on a website can reveal its purpose, whether it's an e-commerce site, a personal blog, a corporate page, or a phishing site.</li>
            <li><b>Sentiment Analysis</b>: Analyzing the tone and sentiment of the content can provide insights into the site's intentions or biases.</li>
            <li><b>Keyword Extraction</b>: Extracting key phrases and words can help identify the main topics and areas of focus, which is useful for further keyword-based searches.</li>
            <li><b>Pivot for Attribution</b>: By identifying specific jargon, themes, or repeated phrases, analysts can link the site to other similar sites or content, potentially leading to the identification of common authors or organizations behind multiple sites.</li>
        </ul>
        """,
        "Extracted Links": """
        <b>Description</b>: Reveals connections to other websites and potential infrastructure.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Network Mapping</b>: Extracting all hyperlinks from a site can help map out its network of connections, revealing related sites, partners, or affiliates.</li>
            <li><b>Hidden Relationships</b>: Discovering links to seemingly unrelated sites can expose hidden relationships or common ownership.</li>
            <li><b>Tracking Infrastructure</b>: Links to external resources (images, scripts, CSS) can identify third-party services in use, providing clues to the website's infrastructure.</li>
            <li><b>Pivot for Attribution</b>: Shared link patterns can indicate a common webmaster or organization, aiding in connecting multiple sites to a single entity.</li>
        </ul>
        """,
        "Domain Information": """
        <b>Description</b>: Offers details about domain ownership and registration.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>WHOIS Lookup</b>: Provides registrant information, including name, organization, address, and contact details. This can be instrumental in identifying the owner.</li>
            <li><b>Domain History</b>: Tools like DomainTools can provide historical data on domain ownership, helping to track changes over time.</li>
            <li><b>Registration Patterns</b>: Analyzing the registration patterns (e.g., registrar, registration date, expiry date) can provide insights into the domain's lifecycle and purpose.</li>
            <li><b>Pivot for Attribution</b>: Cross-referencing WHOIS data with other domains can reveal a common owner or organizational entity, aiding in building a network of connected domains.</li>
        </ul>
        """,
        "DNS Information": """
        <b>Description</b>: Identifies the hosting infrastructure and potential related domains.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>DNS Records</b>: Examining records such as A, MX, CNAME, NS, and TXT can provide insights into the server locations, email servers, and service configurations.</li>
            <li><b>Reverse DNS</b>: Performing reverse DNS lookups can identify other domains hosted on the same IP address, which can indicate related or owned domains.</li>
            <li><b>Subdomains</b>: Identifying subdomains can uncover additional services or sections of a website that are not immediately visible.</li>
            <li><b>Pivot for Attribution</b>: Common DNS records or shared hosting environments can link multiple domains to the same owner or infrastructure, providing a broader picture of their online presence.</li>
        </ul>
        """,
        "MX Information": """
        <b>Description</b>: Indicates email providers and potential communication channels.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Mail Servers</b>: MX records reveal the email servers used by a domain, which can indicate the email provider and security measures in place.</li>
            <li><b>Email Patterns</b>: Understanding the email infrastructure can provide insights into communication habits and potential vulnerabilities.</li>
            <li><b>Pivot for Attribution</b>: Shared MX records across domains can suggest common ownership or administrative control, aiding in mapping an organization's email infrastructure.</li>
        </ul>
        """,
        "Reverse DNS Information": """
        <b>Description</b>: Can reveal hosting patterns and related domains.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>IP to Domain Mapping</b>: Reverse DNS lookups convert IP addresses back to domain names, revealing all domains associated with a given IP.</li>
            <li><b>Shared Hosting Analysis</b>: Identifying multiple domains on the same server can suggest common ownership or a shared hosting service.</li>
            <li><b>Pivot for Attribution</b>: Patterns in reverse DNS results can link multiple domains to a single hosting provider or infrastructure, providing clues to the network behind the domains.</li>
        </ul>
        """,
        "Geolocation Information": """
        <b>Description</b>: Helps in identifying the physical location of the server.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Server Location</b>: Tools like IP geolocation can pinpoint the physical location of the server, which can indicate the jurisdiction and potential regulatory environment.</li>
            <li><b>Regional Analysis</b>: Understanding the server's location can provide context about the site's target audience and operational region.</li>
            <li><b>Pivot for Attribution</b>: Correlating server locations with domain ownership and content can help attribute websites to specific regions or organizations, narrowing down the potential operators.</li>
        </ul>
        """,
        "Oxdork Results": """
        <b>Description</b>: Identifies vulnerabilities and information based on Google dorking.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Advanced Search Techniques</b>: Using Google dorks to uncover sensitive information, such as exposed directories, login pages, and configuration files.</li>
            <li><b>Vulnerability Detection</b>: Identifying misconfigurations, outdated software, and other security vulnerabilities through targeted search queries.</li>
            <li><b>Pivot for Attribution</b>: Discovering unique identifiers or errors across multiple sites can indicate a common development team or webmaster, linking multiple domains together.</li>
        </ul>
        """,
        "Wayback Machine Snapshots": """
        <b>Description</b>: Provides historical data on the website's changes over time.<br/><br/>
        <b>Elaboration</b>:<br/>
        <ul>
            <li><b>Website Evolution</b>: Analyzing historical snapshots to understand how a site has evolved, including changes in content, design, and structure.</li>
            <li><b>Incident Analysis</b>: Identifying when significant changes occurred can help correlate with external events or shifts in strategy.</li>
            <li><b>Pivot for Attribution</b>: Consistent patterns or changes across multiple domains in the Wayback Machine can indicate a common webmaster or organizational control, helping to build a timeline of online activity.</li>
        </ul>
        """
    }


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
        ["Geolocation Information"],
        ["Oxdork Results"],
        ["Wayback Machine Snapshots"]
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
        
        if text in info_text:
            info_header = Paragraph("Info:", ParagraphStyle("InfoHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(info_header)
            info = Paragraph(info_text[text], styleB)
            flowables.append(info)
            flowables.append(Spacer(1, 6))
        
        if text in osint_value:
            osint_header = Paragraph("OSINT Value:", ParagraphStyle("OSINTHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(osint_header)
            osint = Paragraph(osint_value[text], styleB)
            flowables.append(osint)
            flowables.append(Spacer(1, 12))

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
    add_paragraph(text_content[:6000])
    flowables.append(PageBreak())

    add_header("Extracted Links")
    if links:
        links_table = [[Paragraph(link, styleB)] for link in links]
        add_table(links_table, [6*inch])
    else:
        add_paragraph("No extracted links available.")
    flowables.append(PageBreak())

    add_header("Domain Information")
    domain_info_text = """
    <b>Domain Information:</b><br/>
    Every domain that's been registered belongs to someone, and by default, that registration information is public.<br/><br/>

    <b>Registrar:</b> The business that you go to purchase a domain. They handle the reservation of the domain as well as the assignment of IP addresses, such as GoDaddy.<br/><br/>

    <b>Registrant:</b> Is the registered holder of a domain. In order for that person to maintain ownership, they have to pay registration fees.<br/><br/>

    To potentially obtain more information you must go to the Registrar's whois. First, identify the Registrar, then google "registrar's name" + "whois". Do not attempt to use the URL provided next to "WHOIS Server".<br/><br/>

    During an investigation it is often useful to see who has previously owned the domain. Or if you are conducting a Person of Interest or domain investigation and followed the steps above and found that everything has been redacted for privacy due to the use of a privacy guard, a historical whois search may provide unredacted information.<br/><br/>

    There are many historical whois tools. The following have been identified as the best that you can scan for free:<br/>
    <a href="https://www.bigdomaindata.com/">https://www.bigdomaindata.com/</a><br/>
    <a href="https://www.whoxy.com/whois-history/">https://www.whoxy.com/whois-history/</a><br/>
    <a href="https://whois-history.whoisxmlapi.com/">https://whois-history.whoisxmlapi.com/</a>
    """
    flowables.append(Paragraph(domain_info_text, styleB))
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
    mx_info_text = """
    An MX record is what allows someone to send emails from a domain.<br/><br/>

    When investigating a domain for suspicious activity, the existence of an MX record is an early warning sign that the domain is enabled to send email which may be used for a variety of email based attacks.
    """
    flowables.append(Paragraph(mx_info_text, styleB))
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
    flowables.append(PageBreak())

    add_header("Oxdork Results")
    if oxdork_result:
        for result in oxdork_result:
            add_paragraph(result)
    else:
        add_paragraph("No Oxdork results available.")
    flowables.append(PageBreak())

    add_header("Wayback Machine Snapshots")
    if wayback_snapshots:
        for url, timestamp in wayback_snapshots:
            link_text = f'<a href="{url}" color="blue">URL: {url}</a> - Timestamp: {timestamp}'
            flowables.append(Paragraph(link_text, styleB))
    else:
        add_paragraph("No Wayback Machine snapshots available.")

    doc.build(flowables)
    return pdf_file
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

    info_text = {
        "Web Content": "This section displays the first 3000 characters of the web page content.",
        "Extracted Links": "These are all the hyperlinks found on the analyzed web page.",
        "Domain Information": "This information is retrieved from the WHOIS database for the domain.",
        "DNS Information": "These are the A records for the domain, showing its IP addresses.",
        "MX Information": "These are the mail exchanger records for the domain.",
        "Reverse DNS Information": "This shows the domain names associated with the IP addresses.",
        "Geolocation Information": "This provides geographical information based on the IP address.",
        "Oxdork Results": "Results from the oxdork tool.",
        "Wayback Machine Snapshots": "These are historical snapshots of the website."
    }

    osint_value = {
        "Web Content": "Provides insight into the website's purpose and content.",
        "Extracted Links": "Reveals connections to other websites and potential infrastructure.",
        "Domain Information": "Offers details about domain ownership and registration.",
        "DNS Information": "Identifies the hosting infrastructure and potential related domains.",
        "MX Information": "Indicates email providers and potential communication channels.",
        "Reverse DNS Information": "Can reveal hosting patterns and related domains.",
        "Geolocation Information": "Helps in identifying the physical location of the server.",
        "Oxdork Results": "Identifies vulnerabilities and information based on Google dorking.",
        "Wayback Machine Snapshots": "Provides historical data on the website's changes over time."
    }

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
        ["Geolocation Information"],
        ["Oxdork Results"],
        ["Wayback Machine Snapshots"]
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
        
        if text in info_text:
            info_header = Paragraph("Info:", ParagraphStyle("InfoHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(info_header)
            info = Paragraph(info_text[text], styleB)
            flowables.append(info)
            flowables.append(Spacer(1, 6))
        
        if text in osint_value:
            osint_header = Paragraph("OSINT Value:", ParagraphStyle("OSINTHeader", parent=styleB, fontName="Helvetica-Bold"))
            flowables.append(osint_header)
            osint = Paragraph(osint_value[text], styleB)
            flowables.append(osint)
            flowables.append(Spacer(1, 12))

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
    add_paragraph(text_content[:6000])
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
    flowables.append(PageBreak())

    add_header("Oxdork Results")
    if oxdork_result:
        for result in oxdork_result:
            if isinstance(result, dict):
                for query, data in result.items():
                    add_paragraph(f"Query: {query}")
                    if data:
                        data_table = [[Paragraph(item, styleB)] for item in data]
                        add_table(data_table, [6*inch])
                    else:
                        add_paragraph("No results for this query.")
            else:
                add_paragraph(result)
    else:
        add_paragraph("No Oxdork results available.")
    flowables.append(PageBreak())

    add_header("Wayback Machine Snapshots")
    if wayback_snapshots:
        for url, timestamp in wayback_snapshots:
            link_text = f'<a href="{url}" color="blue">URL: {url}</a> - Timestamp: {timestamp}'
            flowables.append(Paragraph(link_text, styleB))
    else:
        add_paragraph("No Wayback Machine snapshots available.")


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
        oxdork_result = run_oxdork(domain)
        wayback_snapshots = fetch_wayback_snapshots(domain)
        print(f"Length of text_content before report creation: {len(text_content)}")

        pdf_file = create_pdf_report(url, web_content, links, text_content, domain_info, dns_info, mx_info, reverse_dns, geo_info, oxdork_result, wayback_snapshots)
        print(f"PDF report generated: {pdf_file}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching web content: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
