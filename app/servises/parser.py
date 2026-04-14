import re

def get_chunks(text: str, max_words: int = 150, overlap: int = 20):
    """
    Разбивает текст на очищенные куски чанки.
    
    :param text: Исходный текст документа.
    :param max_words: Максимальное количество слов в одном чанке (чтобы влезть в лимит токенов).
    :param overlap: Количество слов, которые дублируются в следующем чанке для сохранения контекста.
    :return: Список строк (очищенных чанков).
    """
    

    text = re.sub(r'\s+', ' ', text)
    words = text.strip().split()
    
    if not words:
        return []

    chunks = []
    for i in range(0, len(words), max_words - overlap):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
        
        if i + max_words >= len(words):
            break
            
    return chunks