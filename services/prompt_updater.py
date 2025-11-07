# -*- coding: utf-8 -*-
"""
System Prompts Updater Service
Fetches and updates domain prompts from Google Sheets
"""
import csv
import io
import re
import requests
from typing import Dict, List, Tuple


# Default Google Sheets URL (can be overridden)
DEFAULT_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ohiL6xOBbjC7La2iUdkjrVjG4IEUnVWhI0fRoarD6P0/edit?gid=1507296519"


def extract_sheet_info(sheet_url: str) -> Tuple[str, str, str]:
    """
    Extract sheet ID and gid from Google Sheets URL
    
    Args:
        sheet_url: Full Google Sheets URL
        
    Returns:
        Tuple of (sheet_id, gid, error_message)
    """
    try:
        # Extract sheet ID
        sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not sheet_match:
            return "", "", "URL không hợp lệ: Không tìm thấy spreadsheet ID"
        
        sheet_id = sheet_match.group(1)
        
        # Extract gid (optional, default to 0)
        gid_match = re.search(r'[?&#]gid=(\d+)', sheet_url)
        gid = gid_match.group(1) if gid_match else "0"
        
        return sheet_id, gid, ""
        
    except Exception as e:
        return "", "", f"Lỗi khi parse URL: {str(e)}"


def fetch_prompts_from_sheets(sheet_url: str = None) -> Tuple[Dict[str, Dict[str, str]], str]:
    """
    Fetch system prompts from Google Sheets CSV export
    
    Args:
        sheet_url: Custom Google Sheets URL (optional, uses default if None)
    
    Returns:
        Tuple of (prompts_dict, error_message)
    """
    # Use default URL if not provided
    if sheet_url is None:
        sheet_url = DEFAULT_SHEETS_URL
    
    # Extract sheet ID and gid from URL
    sheet_id, gid, error = extract_sheet_info(sheet_url)
    if error:
        return {}, error
    
    # Build CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        # Fetch CSV from Google Sheets
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Build nested dictionary
        prompts = {}
        row_count = 0
        
        for row in csv_reader:
            domain = row.get('Domain', '').strip()
            topic = row.get('Topic', '').strip()
            system_prompt = row.get('System Prompt', '').strip()
            
            # Skip empty rows
            if not domain or not topic or not system_prompt:
                continue
            
            # Add to nested dict
            if domain not in prompts:
                prompts[domain] = {}
            
            prompts[domain][topic] = system_prompt
            row_count += 1
        
        if row_count == 0:
            return {}, "Không tìm thấy dữ liệu hợp lệ trong CSV"
        
        return prompts, ""
        
    except requests.exceptions.Timeout:
        return {}, "Timeout - vui lòng kiểm tra kết nối internet"
    
    except requests.exceptions.RequestException as e:
        return {}, f"Lỗi mạng: {str(e)}"
    
    except Exception as e:
        return {}, f"Lỗi không xác định: {str(e)}"


def generate_prompts_code(prompts: Dict[str, Dict[str, str]], sheet_url: str = None) -> str:
    """
    Generate Python code for domain_prompts.py from prompts dictionary
    
    Args:
        prompts: Nested dict with structure {domain: {topic: system_prompt}}
        sheet_url: Google Sheets URL for documentation (optional)
    
    Returns:
        Complete Python code for domain_prompts.py
    """
    # Use default URL if not provided
    if sheet_url is None:
        sheet_url = DEFAULT_SHEETS_URL
    
    lines = [
        '# -*- coding: utf-8 -*-',
        '"""',
        'Domain-specific system prompts for video generation',
        f'Auto-generated from Google Sheet: {sheet_url}',
        '"""',
        '',
        '# Domain → Topics → System Prompts mapping',
        'DOMAIN_PROMPTS = {'
    ]
    
    # Sort domains for consistent output
    for domain in sorted(prompts.keys()):
        lines.append(f'    "{domain}": {{')
        
        # Sort topics within each domain
        topics = prompts[domain]
        for topic in sorted(topics.keys()):
            prompt = topics[topic]
            # Escape quotes and backslashes in prompt text
            escaped_prompt = prompt.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'        "{topic}": "{escaped_prompt}",')
        
        lines.append('    },')
    
    lines.append('}')
    lines.append('')
    lines.append('')
    
    # Add utility functions
    lines.append('def get_all_domains():')
    lines.append('    """Get list of all domain names"""')
    lines.append('    return list(DOMAIN_PROMPTS.keys())')
    lines.append('')
    lines.append('')
    lines.append('def get_topics_for_domain(domain):')
    lines.append('    """Get list of topics for a specific domain"""')
    lines.append('    return list(DOMAIN_PROMPTS.get(domain, {}).keys())')
    lines.append('')
    lines.append('')
    lines.append('def get_system_prompt(domain, topic):')
    lines.append('    """Get system prompt for a specific domain and topic"""')
    lines.append('    return DOMAIN_PROMPTS.get(domain, {}).get(topic, "")')
    lines.append('')
    lines.append('')
    lines.append('def build_expert_intro(domain, topic, language="vi"):')
    lines.append('    """Build expert introduction text for script generation')
    lines.append('    ')
    lines.append('    Args:')
    lines.append('        domain: Domain name (e.g., "GIÁO DỤC/HACKS")')
    lines.append('        topic: Topic name (e.g., "Mẹo Vặt (Life Hacks) Độc đáo")')
    lines.append('        language: Language code ("vi" or "en")')
    lines.append('    ')
    lines.append('    Returns:')
    lines.append('        Formatted expert introduction text')
    lines.append('    """')
    lines.append('    system_prompt = get_system_prompt(domain, topic)')
    lines.append('    ')
    lines.append('    if not system_prompt:')
    lines.append('        return ""')
    lines.append('    ')
    lines.append('    if language == "vi":')
    lines.append('        intro = f"""Tôi là chuyên gia trong lĩnh vực {domain}, chuyên về {topic}. ')
    lines.append('Tôi đã nhận ý tưởng từ bạn và sẽ biến nó thành kịch bản và câu chuyện theo yêu cầu của bạn. ')
    lines.append('')
    lines.append('{system_prompt}')
    lines.append('')
    lines.append('Kịch bản như sau:"""')
    lines.append('    else:')
    lines.append('        intro = f"""I am an expert in {domain}, specializing in {topic}. ')
    lines.append('I have received your idea and will turn it into a script and story according to your requirements.')
    lines.append('')
    lines.append('{system_prompt}')
    lines.append('')
    lines.append('Script as follows:"""')
    lines.append('    ')
    lines.append('    return intro')
    lines.append('')
    lines.append('')
    lines.append('def get_all_prompts():')
    lines.append('    """Get all domain-topic-prompt combinations"""')
    lines.append('    result = []')
    lines.append('    for domain, topics in DOMAIN_PROMPTS.items():')
    lines.append('        for topic, prompt in topics.items():')
    lines.append('            result.append({')
    lines.append('                "domain": domain,')
    lines.append('                "topic": topic,')
    lines.append('                "system_prompt": prompt')
    lines.append('            })')
    lines.append('    return result')
    lines.append('')
    lines.append('')
    lines.append('def reload_prompts():')
    lines.append('    """')
    lines.append('    Hot reload prompts by reimporting the module')
    lines.append('    ')
    lines.append('    Returns:')
    lines.append('        tuple: (success: bool, message: str)')
    lines.append('    """')
    lines.append('    try:')
    lines.append('        import importlib')
    lines.append('        import sys')
    lines.append('        ')
    lines.append('        # Get the current module')
    lines.append('        current_module = sys.modules.get(__name__)')
    lines.append('        ')
    lines.append('        if current_module:')
    lines.append('            # Reload the module')
    lines.append('            importlib.reload(current_module)')
    lines.append('            return True, "Đã reload prompts thành công!"')
    lines.append('        else:')
    lines.append('            return False, "Không tìm thấy module để reload"')
    lines.append('            ')
    lines.append('    except Exception as e:')
    lines.append('        return False, f"Lỗi khi reload: {str(e)}"')
    lines.append('')
    
    return '\n'.join(lines)


def update_prompts_file(file_path: str, sheet_url: str = None) -> Tuple[bool, str]:
    """
    Update domain_prompts.py file with latest data from Google Sheets
    
    Args:
        file_path: Path to domain_prompts.py file
        sheet_url: Custom Google Sheets URL (optional, uses default if None)
    
    Returns:
        Tuple of (success, message)
    """
    # Fetch prompts
    prompts, error = fetch_prompts_from_sheets(sheet_url)
    
    if error:
        return False, error
    
    # Generate new code
    new_code = generate_prompts_code(prompts, sheet_url)
    
    # Write to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        
        # Count domains and topics
        domain_count = len(prompts)
        topic_count = sum(len(topics) for topics in prompts.values())
        
        return True, f"Cập nhật thành công! {domain_count} domains, {topic_count} topics"
        
    except Exception as e:
        return False, f"Lỗi khi ghi file: {str(e)}"


if __name__ == "__main__":
    # Test fetching
    prompts, error = fetch_prompts_from_sheets()
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success! Fetched {len(prompts)} domains")
        for domain, topics in prompts.items():
            print(f"  - {domain}: {len(topics)} topics")
