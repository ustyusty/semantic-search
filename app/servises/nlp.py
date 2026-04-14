from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from parser import get_chunks

class NLPService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=self.device)
        self.max_seq_length = self.model.max_seq_length # лимит токенов 

    def _prepare_text(self, text: str):
        """Очистка текста перед обработкой"""
        self.tokenize_and_check(text) # проверяем на лимит токенов
        return " ".join(text.split())

    def tokenize_and_check(self, text: str):
        tokens = self.model.tokenizer.tokenize(text)
        token_count = len(tokens)
        
        if token_count > self.max_seq_length:
            raise ValueError(f"Text size exceeds the limit - {self.max_seq_length}")
        
        return tokens

    def get_embedding(self, text: str) -> list[float]:
        clean_text = self._prepare_text(text)

        embedding = self.model.encode(clean_text, convert_to_numpy=True)
        return embedding.tolist()
    
if __name__ == "__main__":
    nlp_service = NLPService()
    text =  "1. ЦЕЛИ И ЗАДАЧИ\n1.1. Внешний вид сотрудников ООО \"Орион Технолоджис\" является важной составляющей корпоративного имиджа компании и отражает наш профессионализм в глазах клиентов и партнеров.\n1.2. Настоящее положение устанавливает стандарты внешнего вида сотрудников в рабочее время.\n\n2. СТИЛЬ SMART CASUAL (ОФИСНЫЙ ФОРМАТ)\n2.1. В дни, когда у сотрудника не запланированы внешние встречи с клиентами или партнерами, в офисе принят стиль Smart Casual (элегантно-повседневный).\n2.2. Допускается: классические джинсы (без потертостей, дыр и ярких аппликаций), брюки-чинос, юбки средней длины, рубашки с длинным или коротким рукавом, поло, блузки, джемперы, пуловеры, пиджаки и блейзеры свободного кроя. Обувь должна быть чистой и закрытой (лоферы, оксфорды, аккуратные однотонные кеды/кроссовки).\n2.3. Запрещается: спортивные костюмы, шорты, мини-юбки, топы на тонких бретелях, одежда с глубоким декольте, открытая обувь (сланцы, шлепанцы), одежда с агрессивными или нецензурными принтами.\n\n3. СТРОГИЙ ДЕЛОВОЙ СТИЛЬ (ДЛЯ ВСТРЕЧ)\n3.1. При проведении переговоров с клиентами, участии в официальных мероприятиях, конференциях или выставках от лица \"Орион Технолоджис\", сотрудники обязаны придерживаться строгого делового стиля (Business Formal/Business Traditional).\n3.2. Для мужчин: классический деловой костюм (темно-синий, серый, черный), светлая сорочка, галстук (обязателен на протокольных встречах), классические туфли.\n3.3. Для женщин: классический брючный или юбочный костюм, платье-футляр, строгая блузка. Обувь — закрытые туфли-лodочки на умеренном каблуке или классические балетки. Макияж и украшения должны быть сдержанными."
    chunks = get_chunks(text, max_words=30)
    embedding = []
    for chunk in chunks:
        embedding.append(nlp_service.get_embedding(chunk))
    embedding = np.array(embedding)
    mean_embedding = embedding.mean(axis=0)
    print(nlp_service.model.similarity(mean_embedding, embedding))