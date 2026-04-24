# app/services/analyzer.py
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

class SentimentAnalyzer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SentimentAnalyzer, cls).__new__(cls)
            # 모델 및 토크나이저 로드 (snunlp의 금융 전용 모델)
            cls._instance.model_name = "snunlp/KR-FinBERT-SC"
            cls._instance.tokenizer = AutoTokenizer.from_pretrained(cls._instance.model_name)
            cls._instance.model = AutoModelForSequenceClassification.from_pretrained(cls._instance.model_name)
            
            # GPU 사용 가능 시 GPU로 이동
            cls._instance.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            cls._instance.model.to(cls._instance.device)
            cls._instance.model.eval() # 추론 모드
        return cls._instance

    def analyze(self, text: str):
        """
        텍스트를 입력받아 감성 라벨과 상세 확률값을 반환합니다.
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        probs = F.softmax(outputs.logits, dim=-1)
        scores = probs.cpu().numpy()[0]
        
        # 라벨 매핑 (모델 기준: 0:원성/부정, 1:중립, 2:긍정)
        labels = ["negative", "neutral", "positive"]
        label_idx = scores.argmax()
        
        # 감성 점수 계산 (긍정 확률 - 부정 확률) -> -1.0 ~ 1.0 사이 값
        sentiment_score = float(scores[2] - scores[0])
        
        return {
            "label": labels[label_idx],
            "score": sentiment_score,
            "pos": float(scores[2]),
            "neg": float(scores[0]),
            "neu": float(scores[1])
        }

# 사용 예시
# analyzer = SentimentAnalyzer()
# result = analyzer.analyze("삼성전자, 역대급 실적 발표에 주가 급등")