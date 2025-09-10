import faiss
from sentence_transformers import SentenceTransformer
import os
import json

# 감정 문서 데이터
emotion_docs = {
    "공포": "공포는 위험이나 위협에 직면했을 때 느끼는 강렬한 감정입니다. 심장이 뛰고, 식은땀이 나며, 몸이 얼어붙는 듯한 반응을 보입니다.",
    "놀람": "놀람은 예상치 못한 사건이나 정보에 대한 짧고 강렬한 반응입니다. 눈이 커지고, 입이 벌어지는 신체적 반응을 동반합니다.",
    "분노": "분노는 불만이나 적의에 대한 강력한 감정입니다. 얼굴이 붉어지고, 목소리가 커지며, 공격적인 행동을 보일 수 있습니다.",
    "슬픔": "슬픔은 상실, 실망, 절망과 같은 고통스러운 경험에 대한 반응입니다. 눈물이 나고, 무기력감을 느끼며, 의욕이 저하될 수 있습니다.",
    "중립": "중립은 특별한 감정을 느끼지 않는 상태입니다. 차분하고 안정적인 상태로, 감정의 동요가 없습니다.",
    "행복": "행복은 만족감, 기쁨, 즐거움을 느끼는 긍정적인 감정입니다. 웃음, 미소, 활기찬 행동으로 표현됩니다.",
    "혐오": "혐오는 불쾌하거나 역겹거나 반대되는 대상에 대한 강한 거부감입니다. 인상을 찌푸리고, 구역질을 느끼는 등의 반응을 보입니다."
}

# 파일 경로 정의
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE_PATH = os.path.join(BASE_DIR, "emotion_vectors.faiss")
DOCS_FILE_PATH = os.path.join(BASE_DIR, "docs.json")

# 문서와 라벨을 초기화합니다.
doc_labels = []
doc_texts = []
index = None
retriever = None

# DB 파일이 이미 존재하면 로드
if os.path.exists(DB_FILE_PATH) and os.path.exists(DOCS_FILE_PATH):
    print("기존 벡터 데이터베이스 파일을 불러옵니다.")
    index = faiss.read_index(DB_FILE_PATH)
    retriever = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    with open(DOCS_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        doc_labels = data['labels']
        doc_texts = data['texts']
else:
    # 파일이 없으면 새로 구축
    print("새로운 벡터 데이터베이스를 구축합니다...")
    
    doc_labels = list(emotion_docs.keys())
    doc_texts = list(emotion_docs.values())
    
    retriever = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    doc_embeddings = retriever.encode(doc_texts, convert_to_tensor=True).cpu().numpy()
    
    embedding_dim = doc_embeddings.shape[1]
    index = faiss.IndexFlatL2(embedding_dim)
    index.add(doc_embeddings)
    
    # 구축된 인덱스와 문서 데이터를 파일로 저장
    faiss.write_index(index, DB_FILE_PATH)
    with open(DOCS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({'labels': doc_labels, 'texts': doc_texts}, f)
        
    print("벡터 데이터베이스가 성공적으로 구축되어 파일로 저장되었습니다.")