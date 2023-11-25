class AttachmentsController < AuthorizedController
  before_action :set_job
  before_action :set_attachment, only: %i[show edit update destroy]

  add_breadcrumb "Jobs", :jobs_path

  def download
    @attachment = Attachment.find_by(id: params[:attachment_id])
    authorize @attachment

    url = @attachment.file.path

    send_data URI.open(url).read, disposition: :attachment, type: @attachment.file.content_type, filename: @attachment.file_file_name
  end

  def index
    add_breadcrumb "Job", job_path(@job)
    add_breadcrumb "Attachments", job_attachments_path(@job)

    @attachments = policy_scope(Attachment).where(attachable: @job)
    @attachments = @attachments.order(id: :asc).page(params[:page] || 1)
  end

  def show
    authorize @attachment

    add_breadcrumb "Job", job_path(@job)
    add_breadcrumb "Attachments", job_attachments_path(@job)
    add_breadcrumb "Attachment"
  end

  def new
    @attachment = @job.attachments.new
    authorize @attachment

    add_breadcrumb "Job", job_path(@job)
    add_breadcrumb "Attachments", job_attachments_path(@job)
    add_breadcrumb "New"
  end

  def edit
    authorize @attachment

    add_breadcrumb "Job", job_path(@job)
    add_breadcrumb "Attachments", job_attachments_path(@job)
    add_breadcrumb "Attachment", job_attachment_path(@job, @attachment)
    add_breadcrumb "Edit"
  end

  def create
    @attachment = Attachment.new(attachment_params)
    @attachment.attachable_type = "Job"
    @attachment.uploader = current_user

    authorize @attachment

    if @attachment.save
      redirect_to @attachment.attachable, flash: { success: 'Attachment was successfully created.' }
    else
      render :new
    end
  end

  def update
    authorize @attachment

    if @attachment.update(attachment_params)
      redirect_to job_attachments_path(@job), flash: { success: 'Attachment was successfully updated.' }
    else
      render :edit
    end
  end

  def destroy
    authorize @attachment
    @attachment.destroy

    redirect_to job_attachments_url(@job), flash: { success: 'Attachment was successfully destroyed.' }
  end

  private

  def set_job
    @job = Job.find(params[:job_id])
  end

  def set_attachment
    @attachment = Attachment.find(params[:id])
  end

  def attachment_params
    params.require(:attachment).permit(:attachable_id, :user_id, :file, :label)
  end
end
