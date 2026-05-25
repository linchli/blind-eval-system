"""
评测相关 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class ActiveSessionInfo(BaseModel):
    session_id: int
    batch_size: int
    evaluated_in_session: int
    remaining_in_session: int


class EvalStatusResponse(BaseModel):
    total_pairs: int
    evaluated_count: int
    remaining_count: int
    status: str
    active_session: Optional[ActiveSessionInfo] = None
    new_pairs_count: int = 0
    daily_evaluated: int = 0
    suggest_rest: bool = False


class StartSessionResponse(BaseModel):
    session_id: int
    batch_size: int
    pairs: list


class ResumeSessionResponse(BaseModel):
    session_id: int
    batch_size: int
    pairs: list
    next_cursor: int


class EvaluationSubmitRequest(BaseModel):
    pair_id: int
    session_id: int
    score: str
    score_label: str = ""
    is_repeat: int = 0


class EvaluationSubmitResponse(BaseModel):
    evaluation_id: int
    status: str
    score: str


class SubmitRoundRequest(BaseModel):
    session_id: int


class SubmitRoundResponse(BaseModel):
    session_id: int
    total_evaluated: int
    remaining_count: int
    score_distribution: dict


class PairDetailResponse(BaseModel):
    pair_id: int
    scene_name: str = ""
    image_a_url: str
    image_b_url: str
    my_score: Optional[str] = None


class EvaluationOut(BaseModel):
    """单条评测记录输出"""
    id: int
    pair_id: int
    score: str
    score_label: str
    score_a: float
    score_b: float
    created_at: Optional[str] = None


class ProgressOut(BaseModel):
    total_pairs: int
    evaluated_count: int
    remaining_count: int
    progress_percent: int