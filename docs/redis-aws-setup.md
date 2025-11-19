# Redis Setup for AWS Elastic Beanstalk

This guide covers setting up Redis for your backend application deployed on AWS Elastic Beanstalk.

## Overview

For AWS Elastic Beanstalk deployments, we recommend using **AWS ElastiCache for Redis** (managed service) for production. This provides:
- High availability
- Automatic backups
- Security groups integration
- Easy scaling
- Managed maintenance

---

## Option 1: AWS ElastiCache (Recommended)

### Step 1: Create ElastiCache Redis Cluster

1. **Go to AWS Console → ElastiCache**
2. **Click "Create cluster"** → Select **"Redis"**
3. **Configure cluster:**
   - **Name:** `tavily-redis` (or your preferred name)
   - **Engine version:** Latest Redis 7.x or 6.x
   - **Node type:** `cache.t3.micro` (development) or `cache.t3.small` (production)
   - **Number of replicas:** 0 (for single node) or 1+ (for high availability)
   - **Subnet group:** Use the same VPC as your Elastic Beanstalk environment
   - **Security groups:** Create/select a security group (see Step 2)

### Step 2: Configure Security Groups

**Critical:** Your Elastic Beanstalk instances must be able to connect to Redis.

1. **Create or select a security group** for your ElastiCache cluster
2. **Add inbound rule:**
   - **Type:** Custom TCP
   - **Port:** 6379 (default Redis port)
   - **Source:** Select the security group of your Elastic Beanstalk environment
   - **Description:** "Allow Elastic Beanstalk to access Redis"

3. **Verify Elastic Beanstalk security group:**
   - Ensure your EB environment's security group allows outbound connections to port 6379

### Step 3: Get Redis Endpoint

After creating the cluster:
1. Go to **ElastiCache → Redis clusters**
2. Click on your cluster
3. Copy the **Primary endpoint** (e.g., `tavily-redis.xxxxx.0001.use1.cache.amazonaws.com:6379`)

### Step 4: Configure Elastic Beanstalk Environment Variables

**Via AWS Console:**
1. Go to **Elastic Beanstalk → Your Environment → Configuration**
2. Click **Software** → **Edit**
3. Add environment properties:

```bash
USE_REDIS_CACHE=true
REDIS_HOST=tavily-redis.xxxxx.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
# If using Redis AUTH (recommended for production):
REDIS_PASSWORD=your_redis_password_here
```

**Or using REDIS_URL format:**
```bash
USE_REDIS_CACHE=true
REDIS_URL=redis://:password@tavily-redis.xxxxx.0001.use1.cache.amazonaws.com:6379/0
```

**Via EB CLI:**
```bash
eb setenv USE_REDIS_CACHE=true \
         REDIS_HOST=tavily-redis.xxxxx.0001.use1.cache.amazonaws.com \
         REDIS_PORT=6379 \
         REDIS_DB=0 \
         REDIS_PASSWORD=your_password
```

### Step 5: Enable Redis AUTH (Production)

For production, enable Redis AUTH:

1. **When creating cluster:** Enable "AUTH token" and set a password
2. **Or for existing cluster:** Modify cluster → Enable AUTH token
3. **Update environment variable:** `REDIS_PASSWORD=your_secure_password`

**Note:** Store the password in AWS Systems Manager Parameter Store or Secrets Manager for better security.

---

## Option 2: Using .ebextensions Configuration

You can also configure Redis connection via `.ebextensions` config file.

### Create `.ebextensions/redis.config`

```yaml
option_settings:
  aws:elasticbeanstalk:application:environment:
    USE_REDIS_CACHE: 'true'
    REDIS_HOST: 'tavily-redis.xxxxx.0001.use1.cache.amazonaws.com'
    REDIS_PORT: '6379'
    REDIS_DB: '0'
    # REDIS_PASSWORD: 'your_password'  # Use Parameter Store instead
```

**Note:** For sensitive values like passwords, use AWS Systems Manager Parameter Store (see below).

---

## Option 3: Using AWS Systems Manager Parameter Store (Recommended for Secrets)

For better security, store Redis password in Parameter Store:

### Step 1: Create Parameter

```bash
aws ssm put-parameter \
  --name "/tavily/redis/password" \
  --value "your_redis_password" \
  --type "SecureString" \
  --region us-east-1
```

### Step 2: Grant Elastic Beanstalk IAM Role Access

1. Go to **IAM → Roles**
2. Find your Elastic Beanstalk service role (e.g., `aws-elasticbeanstalk-ec2-role`)
3. Attach policy: `AmazonSSMReadOnlyAccess` (or create custom policy for specific parameter)

### Step 3: Use .ebextensions to Fetch Parameter

Create `.ebextensions/redis-secrets.config`:

```yaml
files:
  "/opt/elasticbeanstalk/hooks/appdeploy/pre/01_fetch_redis_password.sh":
    mode: "000755"
    owner: root
    group: root
    content: |
      #!/bin/bash
      REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
      REDIS_PASSWORD=$(aws ssm get-parameter \
        --name "/tavily/redis/password" \
        --with-decryption \
        --region $REGION \
        --query 'Parameter.Value' \
        --output text)
      export REDIS_PASSWORD=$REDIS_PASSWORD

option_settings:
  aws:elasticbeanstalk:application:environment:
    USE_REDIS_CACHE: 'true'
    REDIS_HOST: 'tavily-redis.xxxxx.0001.use1.cache.amazonaws.com'
    REDIS_PORT: '6379'
    REDIS_DB: '0'
```

**Or use environment variable with Parameter Store reference:**
```bash
eb setenv USE_REDIS_CACHE=true \
         REDIS_HOST=tavily-redis.xxxxx.0001.use1.cache.amazonaws.com \
         REDIS_PORT=6379 \
         REDIS_DB=0 \
         REDIS_PASSWORD=$(aws ssm get-parameter --name /tavily/redis/password --with-decryption --query Parameter.Value --output text)
```

---

## VPC Configuration

### Important: Same VPC Required

Your Elastic Beanstalk environment and ElastiCache cluster **must be in the same VPC** for connectivity.

1. **Check your EB environment VPC:**
   - Go to **Elastic Beanstalk → Your Environment → Configuration → Network**
   - Note the VPC ID

2. **Create ElastiCache in same VPC:**
   - When creating ElastiCache cluster, select the same VPC
   - Use appropriate subnets (preferably private subnets)

3. **Subnet Groups:**
   - Create an ElastiCache subnet group with subnets in the same VPC
   - Ensure subnets have proper routing

---

## Testing the Connection

After deployment, test Redis connection:

### Option 1: SSH into EB Instance

```bash
eb ssh
```

Then test Redis:
```bash
python3 -c "
import redis
r = redis.Redis(host='your-redis-endpoint', port=6379, db=0)
r.ping()
print('Redis connection successful!')
"
```

### Option 2: Check Application Logs

Your application will log Redis connection status:
- Success: `"Redis cache connected"`
- Failure: `"Failed to connect to Redis, falling back to in-memory cache"`

Check logs:
```bash
eb logs
```

---

## Connection String Formats

Your application supports multiple Redis connection formats:

### Format 1: Individual Parameters
```bash
USE_REDIS_CACHE=true
REDIS_HOST=your-endpoint.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password
```

### Format 2: REDIS_URL
```bash
USE_REDIS_CACHE=true
REDIS_URL=redis://:password@host:port/db
# Example:
REDIS_URL=redis://:mypassword@tavily-redis.xxxxx.cache.amazonaws.com:6379/0
```

### Format 3: REDIS_URL with AUTH
```bash
USE_REDIS_CACHE=true
REDIS_URL=redis://username:password@host:port/db
```

---

## High Availability Setup

For production, set up Redis with replication:

1. **Create cluster with replicas:**
   - Number of replicas: 1 or more
   - Automatic failover enabled

2. **Use Primary Endpoint:**
   - ElastiCache automatically routes to primary
   - On failover, endpoint updates automatically

3. **Multi-AZ:**
   - Enable Multi-AZ for automatic failover
   - Replicas in different availability zones

---

## Cost Optimization

### Development/Staging:
- Use `cache.t3.micro` (free tier eligible)
- Single node, no replicas
- No backups

### Production:
- Use `cache.t3.small` or larger
- 1+ replicas for HA
- Daily backups enabled
- Multi-AZ enabled

---

## Troubleshooting

### Connection Timeout
- **Check security groups:** Ensure EB security group can access Redis on port 6379
- **Check VPC:** Ensure both are in same VPC
- **Check subnet routing:** Ensure subnets can communicate

### Authentication Failed
- **Verify password:** Check `REDIS_PASSWORD` matches ElastiCache AUTH token
- **Check AUTH enabled:** Ensure AUTH is enabled on cluster

### Fallback to In-Memory Cache
- Application will automatically fall back if Redis unavailable
- Check logs for connection errors
- Verify endpoint and credentials

### Check Redis Status
```bash
# Via AWS Console
ElastiCache → Redis clusters → Your cluster → Status

# Via CLI
aws elasticache describe-cache-clusters --cache-cluster-id your-cluster-id
```

---

## Alternative: Self-Hosted Redis (Not Recommended)

If you need to run Redis on the EB instance itself (not recommended for production):

1. **Install Redis via .ebextensions:**
```yaml
packages:
  yum:
    redis: []

services:
  sysvinit:
    redis:
      enabled: true
      ensureRunning: true
```

2. **Configure environment:**
```bash
USE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Limitations:**
- Not shared across instances (each instance has own cache)
- No high availability
- Not suitable for multi-instance deployments

---

## Summary Checklist

- [ ] Create ElastiCache Redis cluster in same VPC as EB
- [ ] Configure security groups (EB → Redis on port 6379)
- [ ] Enable AUTH token for production
- [ ] Set environment variables in Elastic Beanstalk
- [ ] Test connection via SSH or logs
- [ ] Monitor Redis metrics in CloudWatch
- [ ] Set up backups for production
- [ ] Configure high availability (replicas) for production

---

## Quick Start Commands

```bash
# Set environment variables
eb setenv USE_REDIS_CACHE=true \
         REDIS_HOST=your-endpoint.cache.amazonaws.com \
         REDIS_PORT=6379 \
         REDIS_DB=0

# Deploy
eb deploy

# Check logs
eb logs

# SSH and test
eb ssh
```

---

**For more details, see:**
- [AWS ElastiCache Documentation](https://docs.aws.amazon.com/elasticache/)
- [Elastic Beanstalk Environment Properties](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environments-cfg-softwaresettings.html)

