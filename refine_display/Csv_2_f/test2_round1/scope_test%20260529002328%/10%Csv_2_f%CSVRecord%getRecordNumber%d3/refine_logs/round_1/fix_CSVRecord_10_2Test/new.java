package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_10_2Test {

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long expectedRecordNumber = 5L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, expectedRecordNumber);

        // Act
        long actualRecordNumber = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        // Arrange
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long expectedRecordNumber = 0L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, expectedRecordNumber);

        // Act
        long actualRecordNumber = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testgetRecordNumber_negativeRecordNumber() throws Exception {
        // Arrange
        String[] values = {"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Negative record number";
        long expectedRecordNumber = -1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, expectedRecordNumber);

        // Act
        long actualRecordNumber = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGet_values() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act & Assert
        Assertions.assertEquals("value1", csvRecord.get(0));
        Assertions.assertEquals("value2", csvRecord.get(1));
    }

    @Test
    public void testIsConsistent() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act & Assert
        Assertions.assertTrue(csvRecord.isConsistent());
    }

    @Test
    public void testIsMapped() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act & Assert
        Assertions.assertTrue(csvRecord.isMapped("col1"));
        Assertions.assertFalse(csvRecord.isMapped("col2"));
    }

    @Test
    public void testIsSet() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act & Assert
        Assertions.assertTrue(csvRecord.isSet("col1"));
        Assertions.assertFalse(csvRecord.isSet("col2"));
    }

    @Test
    public void testIterator() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act
        Iterator<String> iterator = csvRecord.iterator();

        // Assert
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testGetComment() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);

        // Act
        String actualComment = csvRecord.getComment();

        // Assert
        Assertions.assertEquals(comment, actualComment);
    }

    @Test
    public void testSize() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act
        int actualSize = csvRecord.size();

        // Assert
        Assertions.assertEquals(2, actualSize);
    }

    @Test
    public void testToString() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        long recordNumber = 1L;
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, recordNumber);

        // Act
        String actualString = csvRecord.toString();

        // Assert
        Assertions.assertEquals("CSVRecord{values=[value1, value2], recordNumber=1}", actualString);
    }
}