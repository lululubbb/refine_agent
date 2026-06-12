package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_4_1Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "First line\r\nSecond line\nThird line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[1024];
        int length = reader.read(buffer, 0, 1024);
        
        Assertions.assertEquals(40, length);
        Assertions.assertEquals("First line\r\nSecond line\nThird line", new String(buffer, 0, length));
        Assertions.assertEquals(3, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Some input"));
        char[] buffer = new char[1024];
        int length = reader.read(buffer, 0, 0);
        
        Assertions.assertEquals(0, length);
        Assertions.assertEquals(0, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        char[] buffer = new char[1024];
        int length = reader.read(buffer, 0, 1024);
        
        Assertions.assertEquals(-1, length);
        Assertions.assertEquals(0, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_singleNewline() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("\n"));
        char[] buffer = new char[1024];
        int length = reader.read(buffer, 0, 1024);
        
        Assertions.assertEquals(1, length);
        Assertions.assertEquals('\n', buffer[0]);
        Assertions.assertEquals(1, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_multipleNewlines() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("\r\n\n\r"));
        char[] buffer = new char[1024];
        int length = reader.read(buffer, 0, 1024);
        
        Assertions.assertEquals(4, length);
        Assertions.assertEquals("\r\n\n\r", new String(buffer, 0, length));
        Assertions.assertEquals(3, invokeGetLineNumber(reader));
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}