import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
from repo_utils import is_valid_repolink, get_reponame, clone_github_repo, create_file_content_dict, delete_directory
from search_utils import make_files_prompt, parse_arr_from_gemini_resp, content_str_from_dict, make_all_files_content_str
from chat_utils import streamer, transform_stlit_to_genai_history

# Repo cloning path
data_dir = './repo'

# configure the model
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# State vars
if "repo_details" not in st.session_state:
    st.session_state.repo_details = {'name': '', 'files2code': {}, 'is_entire_code_loaded': -1, 'entire_code': ''}

if 'title' not in st.session_state:
    st.session_state.title = 'Fill the GitHub Repository link in the sidebar'

if "messages" not in st.session_state:
    st.session_state.messages = []




# Sidebar to fill the link
with st.sidebar:
    repolink = st.text_input("Github Repo Link")
    if st.button("Submit"):
        print("Input received:", repolink)
        if is_valid_repolink(repolink):
            clone_folder = get_reponame(repolink)
            reponame = clone_folder.replace('+', '/')
            
            with st.spinner('1/2 Cloning Repo'):
                repo_clone_path = f"{data_dir}/{clone_folder}"
                clone_github_repo(repolink, repo_clone_path)
            
            
            with st.spinner('2/2 Processing Files'):
                repo_dict = create_file_content_dict(repo_clone_path)
            
            delete_directory(repo_clone_path)
            
            st.success(f'You are ready to chat with repo {reponame}')
            
            st.session_state['repo_details']['name'] = reponame
            st.session_state['repo_details']['files2code'] = repo_dict
            st.session_state['repo_details']['code'] = make_all_files_content_str(repo_dict)
            st.session_state['repo_details']['is_entire_code_loaded'] = -1
            st.session_state['title'] = f"Chat with {reponame}"
        else:
            st.write("Not a valid Github Repo link")
            st.stop()

    
 

st.subheader(f"{st.session_state['title']}")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input(""):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if st.session_state['repo_details']['is_entire_code_loaded'] == -1:
       try:
          num_tokens_code = model.count_tokens(st.session_state['repo_details']['code']).total_tokens
          print(f'Num of tokens in code = {num_tokens_code}')
       except:
          num_tokens_code = 1e6
      
       if num_tokens_code > 1e6-10e3:
          st.session_state['repo_details']['is_entire_code_loaded'] = 0
       else:
          st.session_state['repo_details']['is_entire_code_loaded'] = 1

    prompt_to_use_codebase = "Use the above code if necessary. Preferably answer the below question by citing the filepath and the code"
    if st.session_state['repo_details']['is_entire_code_loaded'] == 0:
      print('Ask Gemini what files might be used')
      files_prompt = make_files_prompt(repo_dict, input)
      response = model.generate_content(files_prompt)
      required_files = parse_arr_from_gemini_resp(response.text)
      print(f'Num of suggested files = {len(required_files)}')
      relevant_code = content_str_from_dict(repo_dict, required_files)
    elif st.session_state['repo_details']['is_entire_code_loaded'] == 1:
        if len(st.session_state['messages']) == 1:
            print('Loading entire codebase')
            relevant_code = st.session_state['repo_details']['code']
        else:
            relevant_code = ''; prompt_to_use_codebase = ''
          
    input_to_LLM = f"'''\n{relevant_code}\n'''\n {prompt_to_use_codebase}.{prompt}?" 
    genai_hist = transform_stlit_to_genai_history(st.session_state.messages, st.session_state['repo_details']['is_entire_code_loaded'], st.session_state['repo_details']['code']) 
    chat = model.start_chat(history=genai_hist)
    gemini_resp = chat.send_message(input_to_LLM, stream=True)
    with st.chat_message("assistant"):
        response = st.write_stream(streamer(gemini_resp))
    st.session_state.messages.append({"role": "assistant", "content": response})


with st.sidebar:
   if st.session_state['repo_details']['is_entire_code_loaded'] != -1:
       if st.button('Change Repo'):
            st.session_state['repo_details'] =  {'name': '', 'files2code': {}, 'is_entire_code_loaded': -1, 'entire_code': ''}
            st.session_state.messages = []
            st.session_state['title'] = 'Fill the GitHub Repository link in the sidebar'