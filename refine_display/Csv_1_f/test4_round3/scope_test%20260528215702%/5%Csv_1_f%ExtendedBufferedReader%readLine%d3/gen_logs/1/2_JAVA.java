package org.apache.commons.csv;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_5_1Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello, World!";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String result = reader.readLine();
        
        Assertions.assertEquals(input, result);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('!', getLastChar(reader));
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String result = reader.readLine();
        
        Assertions.assertEquals("", result);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('\n', getLastChar(reader));
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "First line\nSecond line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        String result = reader.readLine(); // Read end of stream
        
        Assertions.assertNull(result);
        Assertions.assertEquals(2, getLineCounter(reader));
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, getLastChar(reader));
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.readLine(); // Line 1
        reader.readLine(); // Line 2
        String result = reader.readLine(); // Line 3
        
        Assertions.assertEquals("Line 3", result);
        Assertions.assertEquals(3, getLineCounter(reader));
        Assertions.assertEquals('3', getLastChar(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }

    private int getLastChar(ExtendedBufferedReader reader) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}