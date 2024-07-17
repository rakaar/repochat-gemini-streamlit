import re


def make_all_files_content_str(repo_dict):
    formatted_string = ""
    for filepath, content in repo_dict.items():
        formatted_string += f"===\nFilepath: {filepath}\n\n File content:\n{content}\n\n"
    return formatted_string



def make_files_prompt(repo_dict, user_query):
    key_string = "\n".join(repo_dict.keys())
    # print('key string ', key_string, 'dict keys ', repo_dict.keys())
    files_prompt = f"""{key_string}.
Above is the file structure of github codebase. 
To answer {user_query}, what files might be required. 
Reply the filenames as a python array. Your response format should be ['filename1.type, filename2.type']"""
    
    return files_prompt



def parse_arr_from_gemini_resp(text):
    pattern = re.compile(r'\[\s*([\s\S]*?)\s*\]', re.MULTILINE)
    match = pattern.search(text)
    if match:
        array_content = match.group(1)
        array_elements = [element.strip().strip("'\"") for element in array_content.split(',') if element.strip()]
        return array_elements
    else:
        return ['README.md', 'readme.md']
    


def content_str_from_dict(repo_dict, pathnames):
    result = ''
    for path in pathnames:
        content = repo_dict.get(path)
        result += f"===\nFilename: {path}\n\nContent:\n```\n{content}\n```\n===\n"
    return result

