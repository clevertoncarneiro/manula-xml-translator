import sys
import lxml.etree as etree
import textile
import re
import html
from pygoogletranslation import Translator
from datetime import datetime
from progress.bar import Bar


# print current time
def print_time(string):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(string, current_time)


# remove HTML tags with regex
def remove_tags_html(text):
    TAG_HTML = re.compile(r'<[^>]+>')
    return TAG_HTML.sub('', text)


# remove tags based on their start and ending brackets
def remove_between(line, start_string, end_string):
    while 1:
        # pointer that references where is to be removed
        tag_start = line.find(start_string)
        tag_end = line[tag_start:].find(end_string) + tag_start

        # if something gone wrong, break
        if tag_start < 0 or tag_end < 0 or tag_start > tag_end:
            break

        # the substring wanted to be removed
        tag_to_remove = line[tag_start:tag_end + len(end_string)]

        # remove from the string his tag
        line = line.replace(tag_to_remove, '\n')

    return line


# remove tags used by Manula
def remove_tags_manula(line):
    result = line

    # remove more used tags
    result = remove_between(result, '! (', '}}!')
    result = remove_between(result, '(center caption', '}}!')
    result = remove_between(result, '!{IMAGE', '}!')
    result = remove_between(result, '{', '}')

    if result == 'None':
        result = ''

    return result.strip()


def is_inside_brackets(text, start_point):
    # find brackets
    first_bracket_right = text.rfind("{", 0, start_point)
    first_bracket_wrong = text.rfind("}", 0, start_point)
    last_bracket_right = text.find("}", start_point)
    last_bracket_wrong = text.find("{", start_point)

    # say if the translated line is inside the brackets
    if (first_bracket_right > first_bracket_wrong and (
            last_bracket_right < last_bracket_wrong or last_bracket_wrong < 0)
            and first_bracket_right > 0 and last_bracket_right > 0):
        return 1

    return 0


# identify, clean and translate a string
def translate_this(original_text, lng_input, lng_output):
    original_text = original_text.replace("&gt;", ">")
    original_text = original_text.replace("&lt;", "<")
    backup_text = original_text
    return_text = original_text

    backup_text = remove_tags_manula(backup_text)  # remove structures inserted by Manula
    backup_text = textile.textile(backup_text)  # transform textile to html
    backup_text = backup_text.replace("<", "\n<")  # line break to separate tags one per line
    backup_text = remove_tags_html(backup_text)  # remove html tags
    clean_lines = backup_text.splitlines()  # make a list of text lines

    # "clean" a string
    lines_to_translate = []
    for clean_line in clean_lines:
        # modify a html Unicode code to a char Unicode
        clean_line = html.unescape(clean_line)
        clean_line = clean_line.replace('\n', "")
        clean_line = clean_line.replace('\t', "")

        # replace problematic chars, making
        # it different when searching a string to replace
        clean_line = clean_line.replace('“', '"')
        clean_line = clean_line.replace('”', '"')
        clean_line = clean_line.replace('–', '-')
        clean_line = clean_line.replace('×', 'x')
        clean_line = clean_line.replace('&lt;', '\n&lt;')
        clean_line = clean_line.replace('&gt;', '&gt;\n')
        clean_line = clean_line.strip(' ,."-!?:X')
        clean_line = clean_line.strip("'123456789()")

        if not len(clean_line) == 0:
            lines_to_translate.append(clean_line)
            continue

    lines_translated = []
    # keep trying to translate

    for line_to_translate in lines_to_translate:
        while 1:
            try:
                # translate it using Google API
                lines_translated.append(translator.translate(line_to_translate, src=lng_input, dest=lng_output))
                break
            except:
                # do the translation again
                print("!")
                continue

    # for DEBUG purposes
    # if return_text.find(clean_line.strip()) == -1:
    #    continue

    index_pointer = 0
    # replace only one time in the text
    for line_translated in lines_translated:
        # search for the index of the first string to replace
        index_pointer = return_text.find(line_translated.origin, index_pointer)

        # certify the text translated isn't in control structure
        while is_inside_brackets(return_text, index_pointer):
            # find next brackets index
            next_bracket = return_text.find("}", index_pointer)

            # get the next matching string
            index_pointer = return_text.find(line_translated.origin, next_bracket+1)

        return_text = return_text[:index_pointer] \
                      + return_text[index_pointer:].replace(line_translated.origin, line_translated.text, 1)

        index_pointer += len(line_translated.text)

    return return_text


# ----------------------- START OF MAIN CODE ---------------------------
source_filename = str(sys.argv[1])  # input xml file name
lng_input = str(sys.argv[2])  # xml input language
destination_filename = str(sys.argv[3])  # output xml file name
lng_output = str(sys.argv[4])  # xml output language

print_time("Start = ")  # print starting time
parser = etree.XMLParser(strip_cdata=False)  # keep CDATA untouched

with open(source_filename, "rb") as source:  # open xml file
    tree = etree.parse(source, parser)  # open xml tree
    root = tree.getroot()  # get all tags of file
    translator = Translator()  # initialize api

    # to make the progress bar
    all_elements_count = sum(1 for _ in root.iter('content'))
    #all_elements_count += sum(1 for _ in root.iter('keywords'))
    bar = Bar('Processando', max=all_elements_count)

    for content in root.iter('content'):
        with open(destination_filename, "wb") as destination:
            tree.write(destination, encoding="UTF-8", xml_declaration=True)
        bar.next()
        if content.text is not None:
            content.text = etree.CDATA(translate_this(content.text, lng_input, lng_output))

    for keyword in root.iter('keywords'):
        #bar.next()
        if keyword.text is not None:
            keyword.text = etree.CDATA(translate_this(keyword.text, lng_input, lng_output))

    with open(destination_filename, "wb") as destination:
        tree.write(destination, encoding="UTF-8", xml_declaration=True)

bar.finish()
print_time("End = ")  # print final time
