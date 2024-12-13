# Use the latest Ubuntu image
FROM ubuntu:latest

# Set environment variables to prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV HADOOP_HOME=/opt/hadoop
ENV SPARK_HOME=/opt/spark
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH"

# Install necessary tools and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    openjdk-17-jdk \
    git \
    ssh \
    vim \
    net-tools \
    iputils-ping \
    openssh-server \
    gnupg \
    apt-transport-https \
    python3 \
    python3-pip \
    unzip \
    python3-venv && \
    apt-get clean

# Install HashiCorp GPG key and Terraform
RUN wget -O - https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y terraform && \
    apt-get clean

# Install Hadoop
RUN wget https://dlcdn.apache.org/hadoop/common/current/hadoop-3.4.1.tar.gz && \
    tar -xzf hadoop-3.4.1.tar.gz && \
    mv hadoop-3.4.1 /opt/hadoop && \
    rm hadoop-3.4.1.tar.gz

# Install Spark
RUN wget https://dlcdn.apache.org/spark/spark-3.5.3/spark-3.5.3-bin-hadoop3.tgz && \
    tar -xzf spark-3.5.3-bin-hadoop3.tgz && \
    mv spark-3.5.3-bin-hadoop3 /opt/spark && \
    rm spark-3.5.3-bin-hadoop3.tgz

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm awscliv2.zip

# Configure Hadoop and Spark
COPY spark-defaults.conf.template $SPARK_HOME/conf/spark-defaults.conf.template
COPY core-site.xml $HADOOP_HOME/etc/hadoop/core-site.xml
COPY hdfs-site.xml $HADOOP_HOME/etc/hadoop/hdfs-site.xml

# Configure SSH for Hadoop and Spark inter-container communication
RUN ssh-keygen -t rsa -P "" -f ~/.ssh/id_rsa && \
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys && \
    chmod 600 ~/.ssh/authorized_keys

# Copy project folder into the container
COPY ms-dataquality-p /root/ms-dataquality-p

# Set the working directory inside the container
WORKDIR /root/ms-dataquality-p

# Create and activate the virtual environment
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Prepare SSH and virtual environment for use
RUN mkdir -p /run/sshd && chmod 0755 /run/sshd

# Ensure the virtual environment is used in the container
ENV PATH="/opt/venv/bin:$PATH"

# Expose ports for Hadoop and Spark
EXPOSE 8088 9870 9000 7077 8080

# Start SSH service
CMD ["/usr/sbin/sshd", "-D"]