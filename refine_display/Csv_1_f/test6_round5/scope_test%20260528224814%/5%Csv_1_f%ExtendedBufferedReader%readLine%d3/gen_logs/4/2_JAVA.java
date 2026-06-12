package org.apache.commons.csv;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_5_4Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello World\nThis is a test";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        String line2 = reader.readLine();
        Assertions.assertEquals("This is a test", line2);
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "Hello World\n\nThis is a test";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        String line2 = reader.readLine();
        Assertions.assertEquals("", line2);
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "Hello World";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        String line2 = reader.readLine();
        Assertions.assertNull(line2);
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        Assertions.assertEquals("Line 1", reader.readLine());
        Assertions.assertEquals("Line 2", reader.readLine());
        Assertions.assertEquals("Line 3", reader.readLine());
        Assertions.assertNull(reader.readLine());
    }

    @Test
    void testReadLine_withWhitespace() throws Exception {
        String input = "   \n  \n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        Assertions.assertEquals("   ", reader.readLine());
        Assertions.assertEquals("  ", reader.readLine());
        Assertions.assertNull(reader.readLine());
    }

    @Test
    void testReadLine_checkLastChar() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read first line
        String lastCharField = getPrivateFieldValue(reader, "lastChar").toString();
        Assertions.assertEquals('o', lastCharField.charAt(0));

        reader.readLine(); // Read second line
        lastCharField = getPrivateFieldValue(reader, "lastChar").toString();
        Assertions.assertEquals('d', lastCharField.charAt(0));
    }

    private Object getPrivateFieldValue(ExtendedBufferedReader reader, String fieldName) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(reader);
    }
}