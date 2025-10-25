#!/bin/bash

# Blood Bank Management System - Quick Start Script
# This script helps set up and run the application

echo "================================"
echo "Blood Bank Management System"
echo "Quick Start Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install it first."
    exit 1
fi

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL is not installed. Please install it first."
    exit 1
fi

echo "✓ All prerequisites found"
echo ""

# Database Setup
echo "Step 1: Setting up database..."
echo "Please provide your MySQL root password:"
read -s mysql_password

mysql -u root -p"$mysql_password" < database/blood_bank_management.sql
if [ $? -eq 0 ]; then
    echo "✓ Database setup complete"
else
    echo "❌ Database setup failed"
    exit 1
fi

echo ""
echo "Step 2: Setting up backend..."

# Backend Setup
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv env
fi

# Activate virtual environment
source env/bin/activate

# Install requirements
echo "Installing Python packages..."
pip install -q -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✓ Backend packages installed"
else
    echo "❌ Backend setup failed"
    exit 1
fi

# Ask user for MySQL password for backend config
echo ""
echo "Backend Configuration:"
echo "Please enter your MySQL root password (for backend connection):"
read -s backend_password

# Update password in the file (this is a simple approach)
sed -i.bak "s/password='root'/password='$backend_password'/g" blood_bank_fastapi.py

cd ..

echo "✓ Backend setup complete"
echo ""

echo "Step 3: Setting up frontend..."
cd frontend

# Install Node packages
echo "Installing Node packages..."
npm install -q
if [ $? -eq 0 ]; then
    echo "✓ Frontend packages installed"
else
    echo "❌ Frontend setup failed"
    exit 1
fi

cd ..

echo ""
echo "================================"
echo "✓ Setup Complete!"
echo "================================"
echo ""
echo "To run the application:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd backend && source env/bin/activate && python blood_bank_fastapi.py"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd frontend && npm start"
echo ""
echo "Then open: http://localhost:3000"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo ""
