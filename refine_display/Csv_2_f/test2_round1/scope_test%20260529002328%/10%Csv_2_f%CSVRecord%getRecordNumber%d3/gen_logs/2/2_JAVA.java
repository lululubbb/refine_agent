package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

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
}