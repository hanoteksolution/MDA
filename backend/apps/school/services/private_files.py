"""Private, validated attachments; never served by the public media route."""
import hashlib
import io
from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import NotFound, PermissionDenied
from apps.school.models import SchoolFile, ApplicantDocument, StudentDocument, Student, Applicant
from .sis_common import invalid, persist


def root():
    return Path(getattr(settings,'SCHOOL_PRIVATE_ROOT',Path(settings.BASE_DIR)/'private_school_files'))


@transaction.atomic
def upload(uploaded, branch_id, *, access, purpose):
    permission={'admission':'admission_document','student':'student_document','student_photo':'student','applicant_photo':'applicant'}.get(purpose)
    if not permission:invalid('purpose','Choose admission, student, student_photo or applicant_photo.')
    if not (access.allows(permission,'create') or access.allows(permission,'update')):access.require(permission,'create')
    branch=access.campus(branch_id)
    if not uploaded:invalid('file','Choose a file.')
    if uploaded.size>10*1024*1024:invalid('file','Maximum file size is 10 MB.')
    content=uploaded.read(10*1024*1024+1)
    if not content or len(content)>10*1024*1024:invalid('file','Choose a nonempty file up to 10 MB.')
    mime=''
    if content.startswith(b'%PDF-') and purpose in ('admission','student'):
        if b'%%EOF' not in content[-2048:]:invalid('file','The PDF appears incomplete.')
        mime='application/pdf'
    else:
        try:
            with Image.open(io.BytesIO(content)) as img:
                if img.width*img.height>25_000_000:invalid('file','Image dimensions are too large.')
                mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}.get(img.format,'')
                img.verify()
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):invalid('file','Choose a valid PDF, PNG, JPEG or WebP file.')
    if not mime:invalid('file','Unsupported file type.')
    key=f'{access.tenant.pk}/{uuid4().hex}'
    path=root()/key;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(content);path.chmod(0o600)
    try:
        return persist(SchoolFile(tenant=access.tenant,branch=branch,original_name=Path(uploaded.name.replace('\\','/')).name[:200],storage_key=key,content_type=mime,size=len(content),sha256=hashlib.sha256(content).hexdigest()),access,'document_uploaded')
    except Exception:
        path.unlink(missing_ok=True)
        raise


def download(pk,*,access):
    row=SchoolFile.objects.filter(pk=pk,tenant=access.tenant,deleted_at__isnull=True).first()
    if not row:raise NotFound()
    permitted=False
    attached=False
    for model,permission,field in ((ApplicantDocument,'admission_document','file'),(StudentDocument,'student_document','file'),(Student,'student','photo'),(Applicant,'applicant','photo')):
        records=model.objects.filter(**{field:row},deleted_at__isnull=True)
        attached=attached or records.exists()
        if access.allows(permission,'view') and access.scope(records).exists():permitted=True
    if not attached and row.created_by_id==access.user.pk:
        permitted=access.campuses().filter(pk=row.branch_id).exists() and any(access.allows(p,'view') for p in ('admission_document','student_document','student','applicant'))
    if not permitted:raise NotFound()
    path=(root()/row.storage_key).resolve()
    if not path.is_relative_to(root().resolve()) or not path.is_file():raise NotFound()
    return row,path
