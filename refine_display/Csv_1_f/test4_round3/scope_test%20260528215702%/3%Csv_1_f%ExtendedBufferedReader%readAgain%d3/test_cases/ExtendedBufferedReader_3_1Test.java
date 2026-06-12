package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_1Test {

    @Test
    void testReadAgain_initialValue() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals(-2, result);
    }

    @Test
    void testReadAgain_afterReading() throws Exception {
        ExtendedBufferedReader reader = Mockito.spy(new ExtendedBufferedReader(new StringReader("test")));
        reader.read(); // This should set lastChar to the first character's ASCII value

        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('t', result); // 't' is the first character in "test"
    }

    @Test
    void testReadAgain_afterMultipleReads() throws Exception {
        ExtendedBufferedReader reader = Mockito.spy(new ExtendedBufferedReader(new StringReader("test")));
        
        // Reading multiple times to simulate state change
        reader.read();
        reader.read();

        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('e', result); // 'e' is the second character in "test"
    }

    @Test
    void testReadAgain_noReads() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals(-2, result);
    }

    @Test
    void testRead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        int result = reader.read();
        Assertions.assertEquals('t', result); // First character should be 't'
        Assertions.assertEquals(1, reader.getLineNumber()); // Line number should be 1
    }

    @Test
    void testReadLine() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test line"));
        String result = reader.readLine();
        Assertions.assertEquals("test line", result); // The whole line should be read
        Assertions.assertEquals(1, reader.getLineNumber()); // Line number should be 1
    }

    @Test
    void testLookAhead() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('t', result); // Look ahead should return 't'
    }

    @Test
    void testGetLineNumber() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("first line\nsecond line"));
        reader.readLine(); // Read first line
        Assertions.assertEquals(1, reader.getLineNumber()); // Line number should be 1
        reader.readLine(); // Read second line
        Assertions.assertEquals(2, reader.getLineNumber()); // Line number should be 2
    }
}