package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.io.IOException;

class ExtendedBufferedReader_5_2Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello, World!";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String result = reader.readLine();
        
        Assertions.assertEquals(input, result);
        Assertions.assertEquals('!', getPrivateField(reader, "lastChar"));
        Assertions.assertEquals(1, getPrivateField(reader, "lineCounter"));
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String result = reader.readLine();
        
        Assertions.assertEquals("", result);
        Assertions.assertEquals('\n', getPrivateField(reader, "lastChar"));
        Assertions.assertEquals(1, getPrivateField(reader, "lineCounter"));
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "First line\nSecond line\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        String result = reader.readLine(); // Read end of stream
        
        Assertions.assertNull(result);
        Assertions.assertEquals(-1, getPrivateField(reader, "lastChar"));
        Assertions.assertEquals(2, getPrivateField(reader, "lineCounter"));
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        Assertions.assertEquals("Line 1", reader.readLine());
        Assertions.assertEquals("Line 2", reader.readLine());
        Assertions.assertEquals("Line 3", reader.readLine());
        Assertions.assertNull(reader.readLine());
        
        Assertions.assertEquals(-1, getPrivateField(reader, "lastChar"));
        Assertions.assertEquals(3, getPrivateField(reader, "lineCounter"));
    }

    private Object getPrivateField(ExtendedBufferedReader reader, String fieldName) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(reader);
    }
}