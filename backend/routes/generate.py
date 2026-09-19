"""
Generation Routes
Endpoints:
- POST /api/generate      (Generate image txt2img / img2img)
- GET  /api/history       (User's generation history with pagination)
- GET  /api/status/<id>   (Check async job status)
- GET  /api/images/<file> (Serve generated static images)
"""

import os
import base64
import logging
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from models import db, Generation
from routes.auth import token_required
from services.ai_client import ai_client

logger = logging.getLogger('luma.generate')
generate_bp = Blueprint('generate', __name__)

@generate_bp.route('/generate', methods=['POST'])
@token_required
def generate_image(current_user):
    """
    Main image generation endpoint.
    Accepts JSON body with prompt and generation parameters.
    """
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    negative_prompt = data.get('negative_prompt', '').strip()
    mode = data.get('mode', 'txt2img') # 'txt2img' or 'img2img'
    width = int(data.get('width', 512))
    height = int(data.get('height', 512))
    steps = int(data.get('steps', 20))
    cfg_scale = float(data.get('cfg_scale', 7.0))
    seed = int(data.get('seed', -1))
    denoising_strength = float(data.get('denoising_strength', 0.75))
    init_image = data.get('init_image')

    if not prompt:
        return jsonify({'error': 'Bad Request', 'message': 'Prompt is required'}), 400

    if mode == 'img2img' and not init_image:
        return jsonify({'error': 'Bad Request', 'message': 'init_image is required for img2img mode'}), 400

    # Ensure output directory exists
    output_dir = current_app.config['OUTPUT_FOLDER']
    os.makedirs(output_dir, exist_ok=True)

    # 1. Create initial generation record in DB
    job = Generation(
        user_id=current_user.id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        mode=mode,
        status='PROCESSING',
        parameters={
            'width': width,
            'height': height,
            'steps': steps,
            'cfg_scale': cfg_scale,
            'seed': seed,
            'denoising_strength': denoising_strength if mode == 'img2img' else None
        }
    )
    db.session.add(job)
    db.session.commit()

    logger.info(f"Created Generation job {job.id} for user '{current_user.username}', mode: {mode}")

    # 2. Execute generation via AI Client
    try:
        if mode == 'img2img':
            result = ai_client.generate_img2img(
                init_image_base64=init_image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                denoising_strength=denoising_strength,
                seed=seed
            )
        else:
            result = ai_client.generate_txt2img(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed
            )

        # 3. Decode base64 image and save to disk
        image_b64 = result['image_base64']
        filename = f"{job.id}.png"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, 'wb') as img_file:
            img_file.write(base64.b64decode(image_b64))

        # 4. Update job in DB
        job.image_path = filename
        job.status = 'COMPLETED'
        params = job.parameters
        params['actual_seed'] = result.get('seed', seed)
        params['elapsed_seconds'] = result.get('elapsed_seconds', 0)
        job.parameters = params
        db.session.commit()

        logger.info(f"Successfully finished generation job {job.id}, saved image: {filename}")

        return jsonify({
            'job_id': job.id,
            'status': 'COMPLETED',
            'image_url': f"/api/images/{filename}",
            'image_base64': image_b64,
            'prompt': job.prompt,
            'seed': params.get('actual_seed'),
            'elapsed_seconds': params.get('elapsed_seconds'),
            'created_at': job.created_at.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Generation failed for job {job.id}: {e}", exc_info=True)
        job.status = 'FAILED'
        job.error_message = str(e)
        db.session.commit()
        return jsonify({
            'job_id': job.id,
            'status': 'FAILED',
            'error': 'Generation Failed',
            'message': str(e)
        }), 500


@generate_bp.route('/history', methods=['GET'])
@token_required
def get_history(current_user):
    """
    Retrieve paginated generation history for authenticated user.
    Query params:
    - page: int (default: 1)
    - limit: int (default: 12, max: 50)
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(50, max(1, int(request.args.get('limit', 12))))

        pagination = Generation.query.filter_by(user_id=current_user.id)\
            .filter(Generation.status == 'COMPLETED')\
            .order_by(Generation.created_at.desc())\
            .paginate(page=page, per_page=limit, error_out=False)

        items = [gen.to_dict() for gen in pagination.items]

        return jsonify({
            'items': items,
            'total': pagination.total,
            'page': pagination.page,
            'limit': pagination.per_page,
            'total_pages': pagination.pages
        }), 200
    except Exception as e:
        logger.error(f"Error fetching history for user {current_user.id}: {e}")
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@generate_bp.route('/status/<job_id>', methods=['GET'])
@token_required
def get_job_status(current_user, job_id):
    """Check status of a generation job"""
    job = Generation.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({'error': 'Not Found', 'message': 'Job not found'}), 404

    return jsonify(job.to_dict()), 200


@generate_bp.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    """Serve generated images"""
    output_dir = current_app.config['OUTPUT_FOLDER']
    return send_from_directory(output_dir, filename)
