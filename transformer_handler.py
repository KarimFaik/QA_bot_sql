import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForQuestionAnswering

# Инициализация модели и токенизатора
tokenizer = AutoTokenizer.from_pretrained("timpal0l/mdeberta-v3-base-squad2")
model = AutoModelForQuestionAnswering.from_pretrained("timpal0l/mdeberta-v3-base-squad2")

def prepare_inputs(question, context, max_chunk_length=512, overlapped_length=30):
    """
    Подготавливает входные данные для модели, разбивая текст на блоки с перекрытием.
    """
    # Токенизация вопроса и контекста
    tokenized = tokenizer.encode_plus(question, context, add_special_tokens=False)
    tokens = tokenizer.convert_ids_to_tokens(tokenized['input_ids'])

    # Длина вопроса в токенах
    answer_tokens_length = tokenized.token_type_ids.count(0)
    answer_input_ids = tokenized.input_ids[:answer_tokens_length]

    # Длина основного текста первого блока без наложения
    first_context_chunk_length = max_chunk_length - answer_tokens_length
    context_chunk_length = max_chunk_length - answer_tokens_length - overlapped_length

    # Токены основного текста
    context_input_ids = tokenized.input_ids[answer_tokens_length:]
    first = context_input_ids[:first_context_chunk_length]
    others = context_input_ids[first_context_chunk_length:]

    if len(others) > 0:
        padding_length = context_chunk_length - (len(others) % context_chunk_length)
        others += [0] * padding_length
        new_size = (len(others) // context_chunk_length, context_chunk_length)
        new_context_input_ids = np.reshape(others, new_size)
        overlappeds = new_context_input_ids[:, -overlapped_length:]
        overlappeds = np.insert(overlappeds, 0, first[-overlapped_length:], axis=0)
        overlappeds = overlappeds[:-1]
        new_context_input_ids = np.c_[overlappeds, new_context_input_ids]
        new_context_input_ids = np.insert(new_context_input_ids, 0, first, axis=0)
        new_input_ids = np.c_[[answer_input_ids] * new_context_input_ids.shape[0], new_context_input_ids]
    else:
        padding_length = first_context_chunk_length - (len(first) % first_context_chunk_length)
        new_input_ids = np.array([answer_input_ids + first + [0] * padding_length])

    count_chunks = new_input_ids.shape[0]
    new_token_type_ids = [[0] * answer_tokens_length + [1] * (max_chunk_length - answer_tokens_length)] * count_chunks
    new_attention_mask = [[1] * max_chunk_length] * (count_chunks - 1) + [([1] * (max_chunk_length - padding_length)) + ([0] * padding_length)]

    return {
        'input_ids': torch.tensor(new_input_ids),
        'token_type_ids': torch.tensor(new_token_type_ids),
        'attention_mask': torch.tensor(new_attention_mask)
    }, tokens

def get_answer(outputs, tokens, max_chunk_length, answer_tokens_length, overlapped_length):
    """
    Извлекает ответ из выходных данных модели.
    """
    start_index = torch.argmax(outputs.start_logits)
    end_index = torch.argmax(outputs.end_logits)

    start_index = max_chunk_length + (
        start_index - max_chunk_length
        - (answer_tokens_length + overlapped_length)
        * (start_index // max_chunk_length)
    )
    end_index = max_chunk_length + (
        end_index - max_chunk_length
        - (answer_tokens_length + overlapped_length)
        * (end_index // max_chunk_length)
    )

    answer = ''.join([t.replace('▁', ' ') for t in tokens[start_index:end_index+1]])
    return answer

def generate_answer_with_transformer(question, context):
    try:
        # Подготовка входных данных
        inputs, tokens = prepare_inputs(question, context)
        # Извлекаем answer_tokens_length из результата prepare_inputs
        tokenized = tokenizer.encode_plus(question, context, add_special_tokens=False)
        answer_tokens_length = tokenized.token_type_ids.count(0)

        # Получение ответа от модели
        outputs = model(**inputs)

        # Извлечение ответа
        answer = get_answer(outputs, tokens, max_chunk_length=512, answer_tokens_length=answer_tokens_length, overlapped_length=30)

        return answer if answer else "Не удалось найти ответ."
    except Exception as e:
        print(f"Ошибка при генерации ответа: {e}")
        return None