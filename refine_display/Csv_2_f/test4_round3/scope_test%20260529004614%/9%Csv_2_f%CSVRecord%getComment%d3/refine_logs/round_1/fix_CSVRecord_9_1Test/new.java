package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_9_1Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result);
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = ""; // Empty comment
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result);
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null; // Null comment
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertNull(result);
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = " "; // Space as comment
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result);
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        // Arrange
        String[] values = new String[]{"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()"; // Special characters as comment
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String result = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, result);
    }
}