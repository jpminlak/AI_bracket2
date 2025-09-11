// 이메일 기능이 활성화되면 사용하자

//package com.example.demo.inquiry;
//
//import jakarta.mail.*;
//import jakarta.mail.internet.*;
//import java.util.Properties;
//
//public class EmailService {
//
//    public void sendEmail(String to, String subject, String body) throws MessagingException {
//        Properties properties = new Properties();
//        properties.put("mail.smtp.host", "smtp.example.com");
//        properties.put("mail.smtp.port", "587");
//        properties.put("mail.smtp.auth", "true");
//        properties.put("mail.smtp.starttls.enable", "true");
//
//        Session session = Session.getInstance(properties, new Authenticator() {
//            protected PasswordAuthentication getPasswordAuthentication() {
//                return new PasswordAuthentication("your-email@example.com", "your-password");
//            }
//        });
//
//        Message message = new MimeMessage(session);
//        message.setFrom(new InternetAddress("your-email@example.com"));
//        message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(to));
//        message.setSubject(subject);
//        message.setText(body);
//
//        Transport.send(message);
//    }
//}