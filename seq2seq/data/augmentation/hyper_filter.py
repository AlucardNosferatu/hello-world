import jieba
from tqdm import tqdm

from data.augmentation.align import set_QA, concat
from data.augmentation.blacklist import DFAFilter, NaiveFilter, BSFilter
from data.augmentation.frequency import getFreqDist
from data.augmentation.synonyms import sym_of_word, compress_vocab, simplify_sentence
from data.data_tool import Traditional2Simplified


def remove_brackets(lines):
    for i in tqdm(range(len(lines))):
        new_list = []
        temp = lines[i]
        temp_list = temp.split('[')
        for each in temp_list:
            if ']' in each:
                new_list += [each.split(']')[1]]
            else:
                new_list += [each]
        temp_list = new_list
        lines[i] = " ".join(temp_list)
    return lines


def batch_RB():
    with open('../resource/raw/legacy/answer.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    lines = remove_brackets(lines)
    with open('../resource/raw/legacy/answer.txt', 'w', encoding='utf-8') as f:
        f.writelines(lines)


def prompt_filter(show_ng=False, UseAlign=True):
    # region get Dialog
    gfw = DFAFilter()
    gfw.parse("keywords")
    vocab = {}
    words_with_dup = []
    with open('../resource/raw/legacy/unsorted/CPoL4OC.txt', 'r', encoding='utf-8-sig') as q_f:
        if UseAlign:
            lines = q_f.readlines()
        else:
            lines = q_f.read().split('\n')
            lines = lines[:-2]
    q_f = open('../resource/raw/legacy/question.txt', 'a', encoding='utf-8-sig')
    a_f = open('../resource/raw/legacy/answer.txt', 'a', encoding='utf-8-sig')
    print("Loaded.")
    # endregion

    # region get Vocab
    print("Initiate compression.")
    for i in tqdm(range(len(lines))):
        line = lines[i]
        if UseAlign:
            words = jieba.lcut(Traditional2Simplified(line).strip(), cut_all=False)
        else:
            q = line[0].strip() + "\n"
            a = line[1].strip() + "\n"
            words = jieba.lcut(Traditional2Simplified(q).strip(), cut_all=False)
            words += jieba.lcut(Traditional2Simplified(a).strip(), cut_all=False)
        words_with_dup += words
        for word in words:
            vocab[word] = sym_of_word(word)
    fdist = getFreqDist(words_with_dup)
    vocab = compress_vocab(vocab, fdist)
    # endregion

    i = 0
    bound = len(lines)
    if UseAlign:
        bound -= 1
    while i < bound:
        line = lines[i]
        is_ng = gfw.filter(line, '*')
        if not (show_ng ^ is_ng[1]):
            if UseAlign:
                q, a = set_QA(lines, i, gfw, show_ng)
                if a is None:
                    continue
            else:
                line = line.split('\t')
                q = line[0].strip() + "\n"
                a = line[1].strip() + "\n"

            print("问：", q)
            print("答：", a)
            # p = input("是否合格？\n输入y为合格\n输入n为不合格\n输入1为没听懂\n输入1为不认识")
            p = input("是否合格？")
            if p == "n":
                del lines[i]
            elif p == "y":
                q = simplify_sentence(q, vocab)
                a = simplify_sentence(a, vocab)
                q_f.write(q)
                a_f.write(a)
                q_f.flush()
                a_f.flush()
                i += 1

            # region generic replies
            elif p == "1":
                q_f.write(q)
                a = "啥。。。没明白\n"
                a_f.write(a)
                q_f.flush()
                a_f.flush()
                i += 1
            elif p == "2":
                q_f.write(q)
                a = "不认识。。。你说的是谁？\n"
                a_f.write(a)
                q_f.flush()
                a_f.flush()
                i += 1
            # endregion

            elif p.startswith('c'):
                lines, i = concat(p, lines, i, a, gfw, show_ng)
            if p == 'r':
                i -= 1
                if i < 0:
                    i = 0
            else:
                pass
        else:
            del lines[i]
    q_f.close()
    a_f.close()


if __name__ == "__main__":
    prompt_filter()
