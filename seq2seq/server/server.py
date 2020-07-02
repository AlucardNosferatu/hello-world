import json
import pickle
import tensorflow as tf
from tqdm import tqdm
from urllib import parse
from train.utils import load_resource
from infer.infer_seq2seq import build_qa_model
from http.server import SimpleHTTPRequestHandler
from infer.utils import input_question, decode_greedy
from data.obsolete.grammar4fluency import mark_invalid
from data.augmentation.similarity import similarity_complex, Keywords_IoU


class Seq2seq:
    info_log = []
    qa_lines = []
    a_lines_list = []
    similar_answers_from_data = []
    BaseDir = ""
    currentQ = ""
    currentA = ""
    f_r = None
    f_q = None
    f_a = None
    q_model = None
    a_model = None
    word_to_index = None
    index_to_word = None
    all_composed = None
    syn = None
    UseKeywords = False

    def __init__(self, UseKeywords=False, BaseDir='../'):
        self.UseKeywords = UseKeywords
        self.BaseDir = BaseDir
        self.f_r = open(self.BaseDir + "data/resource/raw/all_corpus.tsv", 'r+', encoding='utf-8-sig')
        self.qa_lines = self.f_r.readlines()
        lines = self.qa_lines.copy()
        for i in tqdm(range(len(lines))):
            lines[i] = lines[i].split('\t')[1].replace('\n', '').strip()
            self.a_lines_list = [lines]
        self.q_model, self.a_model = build_qa_model(
            BaseDir=self.BaseDir,
            wp=BaseDir + "train/check_points/W -154-0.0107-.h5"
        )
        _, _, _, _, self.word_to_index, self.index_to_word = load_resource(BaseDir=self.BaseDir)
        self.f_q = open(self.BaseDir + "infer/Online_Q.txt", 'a', encoding='utf-8-sig')
        self.f_a = open(self.BaseDir + "infer/Online_A.txt", 'a', encoding='utf-8-sig')
        with open(BaseDir + 'data/resource/composable.pkl', 'rb') as f:
            self.all_composed = pickle.load(f)
        with open(BaseDir + 'data/resource/syn_dict.pkl', 'rb') as f:
            self.syn = pickle.load(f)
        print(self.interact(new_question="你好"))

    def interact(self, new_question):
        self.currentQ = new_question
        if new_question == 'x':
            self.currentA = "DEBUG:那不打扰你了，回聊~"
            return self.currentA
        new_question, sentence = input_question(
            seq=new_question,
            word_to_index=self.word_to_index,
            all_composed=self.all_composed,
            syn_dict=self.syn
        )
        if sentence is None:
            self.currentA = "DEBUG:" + new_question
            return self.currentA

        with tf.device("/gpu:0"):
            self.currentA = decode_greedy(
                seq=new_question,
                sentence=sentence,
                question_model=self.q_model,
                answer_model=self.a_model,
                word_to_index=self.word_to_index,
                index_to_word=self.index_to_word
            )
        return self.currentA

    def education(self, new_answer):
        if new_answer == "cancel":
            return "取消添加新语料。"
        else:
            self.f_q.write(self.currentQ + "\n")
            self.f_a.write(new_answer + "\n")
            self.f_q.flush()
            self.f_a.flush()
            return "新语料添加成功。"

    def orientation(self, include, exclude):
        self.info_log = []
        if self.UseKeywords:
            include = ""
            exclude = ""
        for j in range(len(self.a_lines_list)):
            self.similar_answers_from_data = []
            for i in range(len(self.a_lines_list[j])):
                line = self.a_lines_list[j][i]
                line = line.replace(' ', '')
                if "【禁用】" in self.qa_lines[i]:
                    continue

                # region use Similarity
                if not self.UseKeywords:
                    if len(exclude) >= 2 and exclude in line:
                        continue
                    if include in line:
                        scores = similarity_complex(line, self.currentA)
                        scores, mean_score, max_score, std_score = scores
                        if max_score > 0.5:
                            self.similar_answers_from_data.append(i)
                            self.info_log.append(" 行号：" + str(i + 1) + " 内容：" + line + " 最高分：" + str(max_score))
                # endregion

                # region Use Keywords
                else:
                    i_o_u, matched = Keywords_IoU(line, self.currentA)
                    if i_o_u >= 0.25 and matched >= 2:
                        self.similar_answers_from_data.append(i)
                        self.info_log.append(
                            " 行号：" + str(i + 1) + " 内容：" + line + " IoU：" + str(i_o_u) + " 相同：" + str(matched))

                # endregion

        return self.similar_answers_from_data, self.info_log

    def correction(self):
        if len(self.similar_answers_from_data) >= 1:
            self.qa_lines = mark_invalid(self.similar_answers_from_data, self.qa_lines)
            self.f_r.truncate(0)
            self.f_r.seek(0)
            self.f_r.writelines(self.qa_lines)
            self.f_r.flush()
            return "被选中语料禁用成功。"
        else:
            return "没有查找到相似回答。"


class MyRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "PSHS/0.1"
    sys_version = "Python/3.7.x"
    seq2seq = Seq2seq(BaseDir='')

    def do_GET(self):

        if self.path == "/":
            print(self.path)
            content = self.seq2seq.currentQ + "\n" + self.seq2seq.currentA
            self.send_response(200)
            self.send_header("Content-type", "json")
            self.end_headers()
            content = content.encode("gbk")
            self.wfile.write(content)
        else:
            print("get path error")

    def do_POST(self):
        if self.path == "/":
            print("postmsg recv, path right")
            data = self.rfile.read(int(self.headers["content-length"]))
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                data = parse.parse_qs(data.decode('utf-8'))
            if data.__contains__('content'):
                response = self.seq2seq.interact(data['content'])
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                res = {'reply': response}
                rspstr = json.dumps(res, ensure_ascii=False)
                self.wfile.write(rspstr.encode("gbk"))
            else:
                self.send_response(500)
                self.send_header("Content-type", "text/html")
                self.end_headers()
        else:
            print("postmsg recv, path error")
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
