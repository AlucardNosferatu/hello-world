import pycorrector
from ltp import LTP


def batch_mark(QingYun=False):
    nlp = LTP()
    # pycorrector.enable_char_error(enable=False)
    if QingYun:
        text_path = "../resource/raw/qingyun_withSyn.tsv"
    else:
        text_path = "../resource/raw/legacy/YellowChick_Q.txt"
        # text_path = "../../infer/Online_Q.txt"
    with open(text_path, 'r+', encoding='utf-8-sig') as f_q:
        with open("../resource/raw/legacy/YellowChick_A.txt", 'r+', encoding='utf-8-sig') as f_a:
            # with open("../../infer/Online_A.txt", 'r+', encoding='utf-8-sig') as f_a:
            q_lines = f_q.readlines()
            a_lines = f_a.readlines()
            for i in range(len(q_lines)):
                if q_lines[i].startswith('【禁用】'):
                    continue
                if QingYun:
                    q = q_lines[i].split('\t')[0].strip()
                    a = q_lines[i].split('\t')[1].replace('\n', '').strip()
                else:
                    q = q_lines[i].replace('\n', '')
                    a = a_lines[i].replace('\n', '')
                # hasName = grammar_analysis(q, nlp)
                has_error = grammar_analysis(a, nlp)
                perplexity, corrected_sent = perplexity_detection(a)
                if perplexity or has_error:
                    print(i, q, a, '\n')
                    choice = input('是否删去？')
                    if choice == 'c':
                        if QingYun:
                            q_lines[i] = q_lines[i].replace(a, corrected_sent)
                        else:
                            a_lines[i] = a_lines[i].replace(a, corrected_sent)
                    elif choice == 'y':
                        if QingYun:
                            pass
                        else:
                            a_lines[i] = '【禁用】' + a_lines[i]
                        q_lines[i] = '【禁用】' + q_lines[i]
                    elif choice == 'q':
                        break
                else:
                    pass
            f_q.truncate(0)
            f_q.seek(0)
            f_q.writelines(q_lines)
            if QingYun:
                pass
            else:
                f_a.truncate(0)
                f_a.seek(0)
                f_a.writelines(a_lines)


def grammar_analysis(sentence, parser):
    segment, hidden = parser.seg([sentence])
    # ner = parser.ner(hidden)
    # print(ner)
    pos = parser.pos(hidden)
    srl = parser.srl(hidden)
    dep = parser.dep(hidden)
    sdp = parser.sdp(hidden)
    suspicion = True
    if suspicion:
        print(segment)
        print("POS: ", pos)
        print("SRL: ", srl)
        print("DEP: ", dep)
        print("SDP: ", sdp)
    return suspicion


def perplexity_detection(src):
    # print(src)
    corrected_sent, detail = pycorrector.correct(src)
    idx_errors = pycorrector.detect(src)
    detected = (len(idx_errors) != 0)
    if detected:
        print(idx_errors)
        print(corrected_sent, detail)
    return detected, corrected_sent


def mark_invalid(invalid_indices, lines):
    for i in invalid_indices:
        lines[i] = "【禁用】" + lines[i]
    return lines


if __name__ == '__main__':
    batch_mark()
