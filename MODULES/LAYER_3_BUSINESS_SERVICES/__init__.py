# LAYER 3: BUSINESS SERVICES
from MODULES.LAYER_3_BUSINESS_SERVICES.ai_client import (
    get_ai_client,
    analyze_attachment,
    attachment_analysis_failed,
    build_initial_question_prompt,
    build_subsequent_question_prompt,
    build_ajax_system_prompt,
    build_evaluation_prompt
)
from MODULES.LAYER_3_BUSINESS_SERVICES.mailer import send_otp_email, send_slot_unlocked_email
from MODULES.LAYER_3_BUSINESS_SERVICES.feedback_email import (
    queue_welcome_email,
    queue_assessment_feedback,
    queue_terminated_notice,
    queue_exit_feedback,
    queue_feedback_notification
)
