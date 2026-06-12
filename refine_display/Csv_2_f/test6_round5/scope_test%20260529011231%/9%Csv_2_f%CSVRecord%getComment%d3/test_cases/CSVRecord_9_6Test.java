package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_9_6Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals("This is a comment", result);
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = ""; // Empty comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals("", result);
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null; // Null comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(null, result); // Expecting null to be equal to null
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+[]{}|;':\",.<>?"; // Special characters
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals("!@#$%^&*()_+[]{}|;':\",.<>?", result);
    }

    @Test
    public void testGetComment_longComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a very long comment that exceeds typical lengths for testing purposes."; // Long comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result);
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = " "; // Single space comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(" ", result); // Assert that a single space is returned
    }

    @Test
    public void testGetComment_veryLongComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = new String(new char[1000]).replace('\0', 'a'); // Very long comment
        long recordNumber = 1;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result); // Assert that the long comment is returned correctly
    }
}