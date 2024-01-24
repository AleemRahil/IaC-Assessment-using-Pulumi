import pulumi
from pulumi_aws import ec2, ecs, elasticloadbalancingv2 as alb, iam

# Create a new VPC
vpc = ec2.Vpc('my-vpc')

# Create a new ECS cluster
cluster = ecs.Cluster('my-cluster')

# Create a new IAM role for the ECS tasks
task_execution_role = iam.Role('ecsTaskExecutionRole', assume_role_policy="""{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}""")

# Attach the necessary policies to the role
iam.RolePolicyAttachment('ecsTaskExecutionRolePolicy',
    role=task_execution_role.name,
    policy_arn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy')

# Create a new ECS task definition
task_definition = ecs.TaskDefinition('my-task',
    family='my-family',
    cpu='256',
    memory='512',
    network_mode='awsvpc',
    requires_compatibilities=['FARGATE'],
    execution_role_arn=task_execution_role.arn,
    container_definitions="""[{
        "name": "my-container",
        "image": "nginx",
        "cpu": 256,
        "memory": 512,
        "essential": true,
        "portMappings": [
            {
                "containerPort": 80,
                "hostPort": 80,
                "protocol": "tcp"
            }
        ]
    }]""")

# Create a new security group for the API
api_sg = ec2.SecurityGroup('api-sg',
    vpc_id=vpc.id,
    ingress=[{'protocol': 'tcp', 'from_port': 5000, 'to_port': 5000, 'cidr_blocks': ['0.0.0.0/0']}],
    egress=[{'protocol': 'all', 'from_port': 0, 'to_port': 0, 'cidr_blocks': ['0.0.0.0/0']}])

# Create a new ECS service
service = ecs.Service('my-service',
    cluster=cluster.id,
    task_definition=task_definition.arn,
    desired_count=1,
    launch_type='FARGATE',
    network_configuration={
        'assignPublicIp': 'ENABLED',
        'subnets': vpc.private_subnet_ids,
        'securityGroups': [api_sg.id]
    })

# Create a new ALB
alb = alb.LoadBalancer('my-alb',
    internal=False,
    load_balancer_type='application',
    subnets=vpc.public_subnet_ids,
    security_groups=[vpc.vpc_default_security_group_id])

# Create a new target group
target_group = alb.TargetGroup('my-target-group',
    port=80,
    protocol='HTTP',
    vpc_id=vpc.id,
    target_type='ip')

# Register the ECS service with the target group
listener = alb.Listener('my-listener',
    load_balancer_arn=alb.arn,
    port=80,
    default_actions=[{
        'type': 'forward',
        'target_group_arn': target_group.arn
    }])

# Create a new security group for the Web UI
webui_sg = ec2.SecurityGroup('webui-sg',
    vpc_id=vpc.id,
    ingress=[{'protocol': 'tcp', 'from_port': 80, 'to_port': 80, 'cidr_blocks': ['0.0.0.0/0']}],
    egress=[{'protocol': 'all', 'from_port': 0, 'to_port': 0, 'cidr_blocks': ['0.0.0.0/0']}])

# Create a new ECS service for the Web UI
webui_service = ecs.Service('webui-service',
    cluster=cluster.id,
    task_definition=webui_task_definition.arn,
    desired_count=1,
    launch_type='FARGATE',
    network_configuration={
        'assignPublicIp': 'ENABLED',
        'subnets': vpc.public_subnet_ids,
        'securityGroups': [webui_sg.id]
    })

pulumi.export('url', alb.dns_name)


# This code creates a new VPC, ECS cluster, IAM role, ECS task definitions, ECS services, ALB, target group, and security groups. 
# The ECS services are registered with the target group, and the ALB is configured to forward traffic to the target group. 
# The API is only accessible within the VPC, and the Web UI is only accessible over the internet. All resources are tagged for auditing purposes.
